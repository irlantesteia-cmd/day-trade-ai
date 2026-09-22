"""
Orquestrador multi-ativo. Roda um loop que a cada ciclo:
1. Busca barras de todos os símbolos/timeframes
2. Calcula features e detecta regime
3. Consulta modelos por timeframe
4. Filtra por risco
5. Aloca capital via Risk Parity
6. Envia ordens para o MT5
"""
import time
import logging
from typing import Dict, List, Any

from src.adapters.multi_market_adapter import MultiMarketAdapter
from src.strategies.multi_tf_strategy import MultiTFStrategy, RegimeDetector
from src.portfolio.risk_parity import RiskParityAllocator
from src.risk.calculators import ATRStopCalculator  # se existir

logger = logging.getLogger(__name__)


class PortfolioOrchestrator:

    def __init__(self, symbols: List[str], timeframes: List[str],
                 models_by_symbol_tf: Dict, feature_keys: List[str],
                 equity: float = 100000.0):
        self.symbols = symbols
        self.timeframes = timeframes
        self.models_by_symbol_tf = models_by_symbol_tf
        self.feature_keys = feature_keys
        self.equity = equity

        self.adapter = MultiMarketAdapter(symbols, timeframes)
        self.allocator = RiskParityAllocator()
        self.regime_detector = RegimeDetector()
        self._strategies: Dict[str, MultiTFStrategy] = {}
        self._returns_hist: Dict[str, List[float]] = {s: [] for s in symbols}
        self._last_close: Dict[str, float] = {}

    def start(self):
        self.adapter.initialize()

    def _features_for(self, symbol: str, bars: List[dict]) -> Dict[str, float]:
        """Calcula features derivadas para uma série de barras."""
        if len(bars) < 21:
            return {}
        closes = [b["close"] for b in bars]
        vols = [b["volume"] for b in bars]
        trs = []
        for i, b in enumerate(bars):
            pc = closes[i - 1] if i > 0 else b["close"]
            trs.append(max(b["high"] - b["low"],
                           abs(b["high"] - pc), abs(b["low"] - pc)))

        c = closes[-1]
        feats = {}
        for lag in (1, 2, 3, 5):
            feats[f"return_{lag}"] = (c - closes[-lag - 1]) / closes[-lag - 1] if closes[-lag - 1] else 0.0
        o, h, l = bars[-1]["open"], bars[-1]["high"], bars[-1]["low"]
        feats["body_pct"] = (c - o) / c if c else 0.0
        feats["range_pct"] = (h - l) / c if c else 0.0
        feats["upper_wick_pct"] = (h - max(o, c)) / c if c else 0.0
        feats["lower_wick_pct"] = (min(o, c) - l) / c if c else 0.0
        avg_vol = sum(vols[-20:]) / 20.0
        feats["vol_ratio_20"] = vols[-1] / avg_vol if avg_vol else 1.0
        atr = sum(trs[-14:]) / 14.0
        feats["atr_14_norm"] = atr / c if c else 0.0

        # Regime one-hot
        regime = self.regime_detector.predict(feats["atr_14_norm"])
        feats["regime"] = regime
        one_hot = self.regime_detector.one_hot(regime)
        feats["regime_calm"] = one_hot[0]
        feats["regime_normal"] = one_hot[1]
        feats["regime_volatile"] = one_hot[2]
        return feats

    def _train_regime(self):
        """Ajusta thresholds de regime com dados iniciais."""
        atrs = []
        for sym in self.symbols:
            bars = self.adapter.fetch_bars(sym, "M15", n=200)
            for b in bars:
                c = b["close"]
                atrs.append((b["high"] - b["low"]) / c if c else 0.0)
        if atrs:
            self.regime_detector.fit(atrs)

    def run_cycle(self) -> List[Any]:
        orders = []
        for sym in self.symbols:
            # Monta features por timeframe
            feats_by_tf = {}
            for tf in self.timeframes:
                bars = self.adapter.fetch_bars(sym, tf, n=50)
                if not bars:
                    continue
                feats = self._features_for(sym, bars)
                if feats:
                    feats_by_tf[tf] = feats

            if not feats_by_tf:
                continue

            # Obtém ou cria estratégia para o símbolo
            if sym not in self._strategies:
                models = self.models_by_symbol_tf.get(sym, {})
                self._strategies[sym] = MultiTFStrategy(
                    models=models, feature_keys=self.feature_keys,
                )
            strat = self._strategies[sym]
            feats_by_tf["symbol"] = sym
            signal = strat.generate_signal(feats_by_tf)

            if signal:
                logger.info("Sinal %s %s conf=%.2f", sym, signal.direction, signal.confidence)
                # Aqui chamaria o RiskManager + ExecutionEngine

        # Alocação de portfólio
        weights = self.allocator.compute_weights(self._returns_hist)
        logger.info("Pesos do portfólio: %s", weights)

        return orders

    def shutdown(self):
        self.adapter.shutdown()