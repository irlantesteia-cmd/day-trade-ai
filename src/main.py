import os
import logging
from typing import Dict, Any, Tuple, Optional

import joblib

from src.adapters.mt5_adapter import MT5Adapter
from src.agents.auditor import TradeAuditor
from src.agents.trainer import AutoRetrainer
from src.config.settings import AppConfig
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order, Signal
from src.engine.kill_switch import KillSwitch
from src.engine.live_engine import LiveTradingEngine
from src.engine.mt5_bridge import MT5ExecutionEngine
from src.risk.engine import RiskEngine
from src.telemetry.alerts import AlertManager
from src.telemetry.collector import MetricsCollector
from src.telemetry.health import SystemHealthMonitor


logger = logging.getLogger(__name__)


FEATURE_KEYS = [
    "return_1", "return_2", "return_3", "return_5",
    "body_pct", "range_pct",
    "upper_wick_pct", "lower_wick_pct",
    "vol_ratio_20", "atr_14_norm",
]


# ---------------------------------------------------------------------------
# Estrategias
# ---------------------------------------------------------------------------

class DummyStrategy:
    """Placeholder. Usada quando nenhum modelo treinado esta disponivel."""

    def generate_signal(self, bar: Dict[str, Any]) -> Any:
        if bar.get("close", 0) > 100.0:
            return Signal(
                symbol=bar.get("symbol", "WIN"),
                direction=SignalDirection.BUY,
                confidence=0.85,
                metadata={"price": bar.get("close")},
            )
        return None


class FeatureMLStrategy:
    """
    Wrapper stateful que calcula features derivadas de uma sequencia de barras
    OHLCV, aplica normalizacao (z-score) e delega para MLSignalStrategy.
    """

    WINDOW = 20

    def __init__(self, ml_strategy, means=None, stds=None):
        self.ml_strategy = ml_strategy
        self._means = means
        self._stds = stds
        self._closes: list = []
        self._volumes: list = []
        self._trs: list = []

    def _compute_features(self, bar: Dict[str, Any]) -> Dict[str, float]:
        o = float(bar["open"])
        h = float(bar["high"])
        l = float(bar["low"])
        c = float(bar["close"])
        v = float(bar.get("volume", 0.0))

        prev_close = self._closes[-1] if self._closes else c

        self._closes.append(c)
        self._volumes.append(v)
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        self._trs.append(tr)

        max_len = self.WINDOW * 2
        if len(self._closes) > max_len:
            self._closes = self._closes[-max_len:]
            self._volumes = self._volumes[-max_len:]
            self._trs = self._trs[-max_len:]

        feats: Dict[str, float] = {}

        for lag in (1, 2, 3, 5):
            if len(self._closes) > lag:
                past = self._closes[-lag - 1]
                feats[f"return_{lag}"] = (c - past) / past if past else 0.0
            else:
                feats[f"return_{lag}"] = 0.0

        feats["body_pct"] = (c - o) / c if c else 0.0
        feats["range_pct"] = (h - l) / c if c else 0.0
        feats["upper_wick_pct"] = (h - max(o, c)) / c if c else 0.0
        feats["lower_wick_pct"] = (min(o, c) - l) / c if c else 0.0

        if len(self._volumes) >= 20:
            avg_vol = sum(self._volumes[-20:]) / 20.0
            feats["vol_ratio_20"] = v / avg_vol if avg_vol else 1.0
        else:
            feats["vol_ratio_20"] = 1.0

        if len(self._trs) >= 14:
            atr = sum(self._trs[-14:]) / 14.0
            feats["atr_14_norm"] = atr / c if c else 0.0
        else:
            feats["atr_14_norm"] = 0.0

        return feats

    def generate_signal(self, bar: Dict[str, Any]) -> Any:
        feats = self._compute_features(bar)
        enriched = dict(bar)
        enriched.update(feats)

        if self._means is not None and self._stds is not None:
            for i, k in enumerate(self.ml_strategy.feature_keys):
                raw = float(enriched.get(k, 0.0))
                enriched[k] = (raw - self._means[i]) / self._stds[i]

        return self.ml_strategy.generate_signal(enriched)


class DummyExecutionEngine:
    def execute_signal(self, signal: Any, bar: Dict[str, Any]) -> Order:
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=1.0,
            price=bar.get("close", 100.0),
            status=OrderStatus.FILLED,
        )


# ---------------------------------------------------------------------------
# Fabrica de estrategia
# ---------------------------------------------------------------------------

def _load_norm(norm_path: str):
    """Le .norm e retorna (means, stds) ou (None, None)."""
    if not os.path.exists(norm_path):
        return None, None
    means, stds = None, None
    with open(norm_path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("means="):
                means = [float(x) for x in line[len("means="):].split(",")]
            elif line.startswith("stds="):
                stds = [float(x) for x in line[len("stds="):].split(",")]
    return means, stds


def _load_strategy():
    """Carrega MLSignalStrategy com normalizacao. Senao, DummyStrategy."""
    model_path = os.getenv("MODEL_PATH", "models/logistic_v1.pkl")
    keys_path = model_path + ".keys"
    norm_path = model_path + ".norm"

    if not os.path.exists(model_path):
        logger.warning("Modelo nao encontrado em %s. Usando DummyStrategy.", model_path)
        return DummyStrategy()

    try:
        from src.strategies import MLSignalStrategy

        model = joblib.load(model_path)

        feature_keys = list(FEATURE_KEYS)
        if os.path.exists(keys_path):
            with open(keys_path, "r") as f:
                parsed = f.read().strip()
                if parsed:
                    feature_keys = parsed.split(",")

        means, stds = _load_norm(norm_path)

        buy_th = float(os.getenv("BUY_THRESHOLD", "0.60"))
        sell_th = float(os.getenv("SELL_THRESHOLD", "0.40"))

        ml = MLSignalStrategy(
            model=model,
            feature_keys=feature_keys,
            buy_threshold=buy_th,
            sell_threshold=sell_th,
        )
        logger.info(
            "MLSignalStrategy carregada de %s (buy=%.2f sell=%.2f, %d features, norm=%s)",
            model_path, buy_th, sell_th, len(feature_keys),
            "sim" if means else "nao",
        )
        return FeatureMLStrategy(ml, means=means, stds=stds)

    except Exception as exc:
        logger.warning("Falha ao carregar modelo (%s). Usando DummyStrategy.", exc)
        return DummyStrategy()


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------

def build_system(config: Optional[AppConfig] = None, use_mt5: bool = False) -> Dict[str, Any]:
    cfg = config or AppConfig.from_env()

    metrics = MetricsCollector()
    health = SystemHealthMonitor(metrics)
    alerts = AlertManager()
    strategy = _load_strategy()
    auditor = TradeAuditor()
    retrainer = AutoRetrainer(min_samples=5)
    risk_engine = RiskEngine()

    if use_mt5 or cfg.trading_mode in ["live", "paper_mt5"]:
        mt5_adapter = MT5Adapter()
        mt5_adapter.initialize()
        execution = MT5ExecutionEngine(adapter=mt5_adapter)
    else:
        execution = DummyExecutionEngine()

    engine = LiveTradingEngine(
        strategy=strategy,
        risk_manager=None,
        execution_engine=execution,
        metrics_collector=metrics,
        health_monitor=health,
        risk_engine=risk_engine,
    )

    kill_switch = KillSwitch(engine, max_daily_loss=cfg.max_daily_loss)
    alerts.register_handler(kill_switch.handle_alert)

    return {
        "config": cfg,
        "metrics": metrics,
        "health": health,
        "alerts": alerts,
        "engine": engine,
        "kill_switch": kill_switch,
        "auditor": auditor,
        "retrainer": retrainer,
    }


def run_app(config: Optional[AppConfig] = None, use_mt5: bool = False) -> Tuple[Dict[str, Any], Any]:
    system = build_system(config, use_mt5=use_mt5)
    engine = system["engine"]
    auditor = system["auditor"]
    retrainer = system["retrainer"]

    engine.start()
    sample_bar = {"symbol": "WIN", "open": 105.0, "high": 106.0, "low": 104.0,
                  "close": 105.5, "volume": 1500.0}
    order = engine.process_bar(sample_bar)

    if order and getattr(order, "status", None) == OrderStatus.FILLED:
        auditor.record_trade(
            order=order,
            features_snapshot={"close": sample_bar["close"]},
            expected_price=105.0,
            pnl=10.0,
        )
        retrainer.evaluate_and_retrain(auditor.trade_history)

    return system, order


if __name__ == "__main__":
    run_app()