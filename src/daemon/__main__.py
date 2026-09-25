"""
Entry point do daemon: python -m src.daemon

Suporta duas estrategias:
  --strategy default   -> MLSignalStrategy ou DummyStrategy (comportamento antigo)
  --strategy ensemble  -> EnsembleStrategy + DynamicPositionSizer + EnsembleLiveAdapter

Uso:
    python -m src.daemon --symbol WINV26 --mode paper_mt5 --strategy ensemble
    python -m src.daemon --symbol WINV26 --mode paper_mt5 --strategy default
"""
import argparse
import logging
from typing import Any, Dict, Optional

from src.adapters.mt5_adapter import MT5Adapter
from src.daemon.runner import DaemonRunner
from src.daemon.scheduler import Scheduler
from src.daemon.state import StateStore
from src.indicators.engine import IndicatorEngine
from src.main import build_system
from src.risk.dynamic_sizing import DynamicPositionSizer


logger = logging.getLogger(__name__)


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daemon 24/7 do Day Trade AI Platform")
    parser.add_argument("--symbol", default="WINV26", help="Simbolo a operar")
    parser.add_argument(
        "--mode",
        choices=["paper", "paper_mt5"],
        default="paper_mt5",
        help="Modo de execucao (live desabilitado por design)",
    )
    parser.add_argument(
        "--strategy",
        choices=["default", "ensemble"],
        default="default",
        help="Estrategia: default (ML) ou ensemble (MA+RSI+VB+RFMA)",
    )
    parser.add_argument("--poll", type=float, default=5.0, help="Segundos entre polls")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--state-path",
        default="data/daemon_state.db",
        help="Caminho do SQLite de estado",
    )
    parser.add_argument(
        "--snapshot-interval",
        type=float,
        default=60.0,
        help="Segundos entre snapshots de estado",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Se definido, para apos N iteracoes (util em testes)",
    )
    # Parametros do ensemble
    parser.add_argument(
        "--ensemble-mode",
        choices=["vote", "weighted", "unanimous", "confidence_weighted"],
        default="vote",
    )
    parser.add_argument("--min-agreement", type=float, default=0.5)
    parser.add_argument(
        "--include-regime-filtered", action="store_true", default=True)
    parser.add_argument(
        "--warmup-bars",
        type=int,
        default=60,
        help="Barras historicas a alimentar no buffer antes do loop (default 60)",
    )
    # Parametros do dynamic sizer
    parser.add_argument("--base-risk-pct", type=float, default=1.0)
    parser.add_argument("--vol-target-pct", type=float, default=0.5)
    return parser.parse_args(argv)


def _build_ensemble_strategy(args) -> Any:
    """Constroi EnsembleStrategy envolvido em EnsembleLiveAdapter."""
    from src.strategies.ensemble_strategy import EnsembleStrategy
    from src.strategies.ensemble_live_adapter import EnsembleLiveAdapter

    internal = EnsembleStrategy(
        mode=args.ensemble_mode,
        min_agreement=args.min_agreement,
        min_confidence=0.5,
        include_regime_filtered=args.include_regime_filtered,
    )
    adapter = EnsembleLiveAdapter(
        internal_strategy=internal,
        indicator_engine=IndicatorEngine(),
        max_buffer=500,
        min_history=50,
    )
    logger.info(
        "EnsembleStrategy configurada: mode=%s, min_agreement=%.2f, "
        "include_regime_filtered=%s",
        args.ensemble_mode, args.min_agreement, args.include_regime_filtered,
    )
    return adapter


def _build_dynamic_sizer(args) -> Any:
    sizer = DynamicPositionSizer(
        base_risk_pct=args.base_risk_pct,
        vol_target_pct=args.vol_target_pct,
        confidence_scaling=True,
    )
    logger.info(
        "DynamicPositionSizer configurado: base_risk=%.2f%%, vol_target=%.2f%%",
        args.base_risk_pct, args.vol_target_pct,
    )
    return sizer


def _warmup_ensemble_buffer(
    strategy: Any,
    bar_source: MT5Adapter,
    symbol: str,
    n_bars: int = 60,
) -> int:
    """
    Alimenta o buffer do EnsembleLiveAdapter com N barras historicas.

    Chama strategy.generate_signal(bar) com cada barra historica. O
    adapter internamente constroi o buffer. Retorna quantas barras
    foram carregadas com sucesso.

    Requer que a estrategia exponha um metodo generate_signal.
    """
    if not hasattr(strategy, "generate_signal"):
        return 0

    # Busca barras historicas. Usamos copy_rates_from_pos direto.
    try:
        import MetaTrader5 as mt5
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, n_bars)
        if rates is None or len(rates) == 0:
            logger.warning("Warmup: sem barras para %s", symbol)
            return 0
    except Exception as exc:
        logger.warning("Warmup: falha ao buscar barras (%s)", exc)
        return 0

    loaded = 0
    for r in rates:
        bar = {
            "symbol": symbol,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["tick_volume"]),
            "timestamp": int(r["time"]),
        }
        try:
            strategy.generate_signal(bar)
            loaded += 1
        except Exception:
            pass
    return loaded


def main(argv=None) -> Dict[str, Any]:
    args = _parse_args(argv)
    _setup_logging(args.log_level)

    logger.info(
        "Daemon iniciando: symbol=%s mode=%s strategy=%s poll=%.1fs state=%s",
        args.symbol, args.mode, args.strategy, args.poll, args.state_path,
    )

    # 1. StateStore
    store = StateStore(args.state_path)

    # 2. Estrategia + sizer
    use_mt5 = args.mode == "paper_mt5"

    if args.strategy == "ensemble":
        strategy = _build_ensemble_strategy(args)
        sizer = _build_dynamic_sizer(args)
    else:
        strategy = None  # build_system resolve via _load_strategy
        sizer = None

    # 3. build_system
    system = build_system(use_mt5=use_mt5, strategy=strategy, sizer=sizer)
    engine = system.get("engine")
    if engine is None:
        raise RuntimeError("build_system nao retornou engine")

    # 4. bar source
    bar_source = MT5Adapter()
    if use_mt5:
        if not bar_source.initialize():
            logger.warning("MT5 init inicial falhou - daemon tentara reconnect no loop")

    # 5a. Warmup: alimenta o buffer do adapter com barras historicas
    if args.strategy == "ensemble" and args.warmup_bars > 0:
        try:
            warmup_ok = _warmup_ensemble_buffer(
                strategy=strategy,
                bar_source=bar_source,
                symbol=args.symbol,
                n_bars=args.warmup_bars,
            )
            logger.info("Warmup: %d barras carregadas no buffer", warmup_ok)
        except Exception as exc:
            logger.warning("Warmup falhou (%s). Ensemble pode nao emitir sinais.", exc)

    # 5b. engine.start
    engine.start()

    # 6. tick_fn
    last_ts: Dict[str, Optional[int]] = {"value": None}
    processed: Dict[str, int] = {"count": 0}

    def tick() -> None:
        bar = bar_source.fetch_latest_bar(args.symbol)
        if not bar:
            return
        ts = bar.get("timestamp")
        if ts == last_ts["value"]:
            return

        last_ts["value"] = ts
        processed["count"] += 1
        logger.info(
            "[%d] %s @ %s | close=%s",
            processed["count"], args.symbol, ts, bar.get("close"),
        )
        order = engine.process_bar(bar)
        if order is not None:
            logger.info("Ordem executada: %s", order)

    # 7. reconnect_fn
    def reconnect() -> bool:
        logger.warning("Tentando reconnect do MT5...")
        try:
            bar_source.shutdown()
        except Exception:
            pass
        return bar_source.initialize()

    # 8. Scheduler
    scheduler = Scheduler()

    # 9. Persiste config inicial
    store.save_daemon_config({
        "symbol": args.symbol,
        "mode": args.mode,
        "strategy": args.strategy,
        "poll": args.poll,
        "ensemble_mode": args.ensemble_mode if args.strategy == "ensemble" else None,
    })

    # 10. Runner
    runner = DaemonRunner(
        tick_fn=tick,
        reconnect_fn=reconnect,
        state_store=store,
        scheduler=scheduler,
        poll_interval_sec=args.poll,
        snapshot_interval_sec=args.snapshot_interval,
    )

    try:
        stats = runner.run(max_iterations=args.max_iterations)
    finally:
        try:
            engine.stop()
        except Exception:
            logger.exception("Falha ao parar engine")
        try:
            bar_source.shutdown()
        except Exception:
            pass
        try:
            store.close()
        except Exception:
            pass

    logger.info("Daemon finalizado: %s", stats)
    return stats


if __name__ == "__main__":
    main()