"""
Entry point do daemon: python -m src.daemon

Liga tudo:
  - build_system (mesmo pipeline do CLI)
  - StateStore (persistencia)
  - Scheduler (tarefas periodicas)
  - DaemonRunner (loop resiliente)

Uso:
    python -m src.daemon --symbol WINV26 --mode paper_mt5
    python -m src.daemon --symbol WINV26 --mode paper_mt5 --poll 5.0
"""
import argparse
import logging
import time
from typing import Any, Dict, Optional

from src.adapters.mt5_adapter import MT5Adapter
from src.daemon.runner import DaemonRunner
from src.daemon.scheduler import Scheduler
from src.daemon.state import StateStore
from src.main import build_system


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
    return parser.parse_args(argv)


def main(argv=None) -> Dict[str, Any]:
    args = _parse_args(argv)
    _setup_logging(args.log_level)

    logger.info(
        "Daemon iniciando: symbol=%s mode=%s poll=%.1fs state=%s",
        args.symbol, args.mode, args.poll, args.state_path,
    )

    # 1. StateStore
    store = StateStore(args.state_path)

    # 2. build_system
    use_mt5 = args.mode == "paper_mt5"
    system = build_system(use_mt5=use_mt5)
    engine = system.get("engine")
    if engine is None:
        raise RuntimeError("build_system nao retornou engine")

    # 3. adapters / bar source
    bar_source = MT5Adapter()
    if use_mt5:
        if not bar_source.initialize():
            logger.warning("MT5 init inicial falhou — daemon tentara reconnect no loop")

    # 4. engine.start
    engine.start()

    # 5. tick_fn: busca barra e processa
    last_ts: Dict[str, Optional[int]] = {"value": None}
    processed: Dict[str, int] = {"count": 0}

    def tick() -> None:
        bar = bar_source.fetch_latest_bar(args.symbol)
        if not bar:
            return
        ts = bar.get("timestamp")
        if ts == last_ts["value"]:
            return  # barra inalterada

        last_ts["value"] = ts
        processed["count"] += 1
        logger.info(
            "[%d] %s @ %s | close=%s",
            processed["count"], args.symbol, ts, bar.get("close"),
        )
        order = engine.process_bar(bar)
        if order is not None:
            logger.info("Ordem executada: %s", order)

    # 6. reconnect_fn: reinicializa MT5
    def reconnect() -> bool:
        logger.warning("Tentando reconnect do MT5...")
        try:
            bar_source.shutdown()
        except Exception:
            pass
        return bar_source.initialize()

    # 7. Scheduler
    scheduler = Scheduler()

    # 8. Persiste config inicial
    store.save_daemon_config({
        "symbol": args.symbol,
        "mode": args.mode,
        "poll": args.poll,
    })

    # 9. Runner
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
        # Cleanup: para engine e fecha store
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