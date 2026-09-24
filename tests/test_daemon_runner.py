"""Testes do DaemonRunner (loop resiliente do daemon)."""
import os
import tempfile

import pytest

from src.daemon.runner import DaemonRunner
from src.daemon.scheduler import Scheduler
from src.daemon.state import StateStore


def _no_sleep(s: float) -> None:
    pass


# ---------------------------------------------------------------------------
# Validacao de parametros
# ---------------------------------------------------------------------------

def test_invalid_poll_interval_raises():
    with pytest.raises(ValueError):
        DaemonRunner(tick_fn=lambda: None, poll_interval_sec=0)


def test_invalid_backoff_raises():
    with pytest.raises(ValueError):
        DaemonRunner(tick_fn=lambda: None, reconnect_backoff_sec=0)


def test_max_backoff_less_than_initial_raises():
    with pytest.raises(ValueError):
        DaemonRunner(
            tick_fn=lambda: None,
            reconnect_backoff_sec=10.0,
            max_reconnect_backoff_sec=5.0,
        )


# ---------------------------------------------------------------------------
# Loop basico
# ---------------------------------------------------------------------------

def test_run_executes_tick_per_iteration():
    calls = []
    runner = DaemonRunner(
        tick_fn=lambda: calls.append(1),
        sleep_fn=_no_sleep,
    )
    stats = runner.run(max_iterations=3)
    assert len(calls) == 3
    assert stats["iterations"] == 3
    assert stats["ticks_ok"] == 3
    assert stats["ticks_failed"] == 0


def test_run_returns_final_stats():
    runner = DaemonRunner(tick_fn=lambda: None, sleep_fn=_no_sleep)
    stats = runner.run(max_iterations=2)
    assert stats == {
        "iterations": 2,
        "ticks_ok": 2,
        "ticks_failed": 0,
        "reconnects_ok": 0,
        "reconnects_failed": 0,
    }


def test_run_with_zero_iterations():
    calls = []
    runner = DaemonRunner(
        tick_fn=lambda: calls.append(1),
        sleep_fn=_no_sleep,
    )
    stats = runner.run(max_iterations=0)
    assert stats["iterations"] == 0
    assert calls == []


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------

def test_request_shutdown_stops_loop():
    runner = DaemonRunner(tick_fn=lambda: None, sleep_fn=_no_sleep)
    calls = []

    def tick():
        calls.append(1)
        if len(calls) >= 2:
            runner.request_shutdown()

    runner.tick_fn = tick
    stats = runner.run(max_iterations=100)
    assert stats["iterations"] == 2
    assert len(calls) == 2


def test_is_shutdown_requested_flag():
    runner = DaemonRunner(tick_fn=lambda: None, sleep_fn=_no_sleep)
    assert runner.is_shutdown_requested() is False
    runner.request_shutdown()
    assert runner.is_shutdown_requested() is True


# ---------------------------------------------------------------------------
# Falhas e reconnect
# ---------------------------------------------------------------------------

def test_tick_failure_increments_counter_and_calls_reconnect():
    calls = []
    reconnect_calls = []

    def failing_tick():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")

    def reconnect():
        reconnect_calls.append(1)
        return True

    runner = DaemonRunner(
        tick_fn=failing_tick,
        reconnect_fn=reconnect,
        sleep_fn=_no_sleep,
        reconnect_backoff_sec=1.0,
        max_reconnect_backoff_sec=10.0,
    )
    stats = runner.run(max_iterations=3)

    assert stats["iterations"] == 3
    assert stats["ticks_ok"] == 2
    assert stats["ticks_failed"] == 1
    assert stats["reconnects_ok"] == 1
    assert len(reconnect_calls) == 1


def test_reconnect_failure_increments_and_backs_off():
    """
    Verifica backoff exponencial: 1, 2, 4, 8 (capado).

    O sleep_fn e chamado duas vezes por iteracao (backoff + poll).
    Uso poll_interval_sec grande para separar os valores.
    """
    sleeps = []
    runner = DaemonRunner(
        tick_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        reconnect_fn=lambda: False,
        sleep_fn=lambda s: sleeps.append(s),
        poll_interval_sec=99.0,  # poll grande, filtra depois
        reconnect_backoff_sec=1.0,
        max_reconnect_backoff_sec=8.0,
    )
    stats = runner.run(max_iterations=4)

    assert stats["ticks_failed"] == 4
    assert stats["reconnects_failed"] == 4

    backoff_sleeps = [s for s in sleeps if s != 99.0]
    assert backoff_sleeps == [1.0, 2.0, 4.0, 8.0]


def test_reconnect_success_resets_backoff():
    """
    Falha, falha (com reconnect OK na 2a), falha. Backoff deve voltar
    ao valor base apos reconnect bem-sucedido.
    """
    sleeps = []
    fail_plan = [True, True, True, False]  # falha nas 3 primeiras
    idx = {"i": 0}
    reconnect_plan = [False, True, False, True]  # reconnect alterna
    r_idx = {"i": 0}

    def tick():
        i = idx["i"]
        idx["i"] += 1
        if fail_plan[min(i, len(fail_plan) - 1)]:
            raise RuntimeError("boom")

    def reconnect():
        j = r_idx["i"]
        r_idx["i"] += 1
        return reconnect_plan[min(j, len(reconnect_plan) - 1)]

    runner = DaemonRunner(
        tick_fn=tick,
        reconnect_fn=reconnect,
        sleep_fn=lambda s: sleeps.append(s),
        poll_interval_sec=99.0,
        reconnect_backoff_sec=1.0,
        max_reconnect_backoff_sec=10.0,
    )
    runner.run(max_iterations=4)

    backoff_sleeps = [s for s in sleeps if s != 99.0]
    # Iter 1: falha, reconnect False -> sleep(1), retorna 2
    # Iter 2: falha, reconnect True  -> sem sleep, retorna 1 (reset)
    # Iter 3: falha, reconnect False -> sleep(1), retorna 2
    # Iter 4: ok (nao chama reconnect)
    assert backoff_sleeps == [1.0, 1.0]


def test_reconnect_exception_handled_as_failure():
    runner = DaemonRunner(
        tick_fn=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        reconnect_fn=lambda: (_ for _ in ()).throw(RuntimeError("reconnect boom")),
        sleep_fn=_no_sleep,
        reconnect_backoff_sec=1.0,
        max_reconnect_backoff_sec=10.0,
    )
    stats = runner.run(max_iterations=2)
    assert stats["ticks_failed"] == 2
    assert stats["reconnects_failed"] == 2


# ---------------------------------------------------------------------------
# Scheduler integrado
# ---------------------------------------------------------------------------

def test_scheduler_runs_during_loop():
    """
    Usa sleep real minimo para garantir que time.monotonic() avance
    entre iteracoes (Windows tem resolucao ~15ms).
    """
    import time as _time

    sch = Scheduler()
    task_runs = []
    sch.every(0.001, "task", lambda: task_runs.append(1))

    runner = DaemonRunner(
        tick_fn=lambda: None,
        scheduler=sch,
        sleep_fn=lambda s: _time.sleep(0.02),
    )
    runner.run(max_iterations=3)
    assert len(task_runs) == 3


# ---------------------------------------------------------------------------
# StateStore integrado
# ---------------------------------------------------------------------------

def test_state_store_saves_heartbeat():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.db")
        store = StateStore(path)
        sch = Scheduler()

        runner = DaemonRunner(
            tick_fn=lambda: None,
            state_store=store,
            scheduler=sch,
            snapshot_interval_sec=1e-9,
            sleep_fn=_no_sleep,
        )
        runner.run(max_iterations=3)

        hb = store.load_heartbeat()
        assert hb is not None
        assert hb["source"] == "daemon_loop"

        store.close()


def test_state_store_saves_final_kill_switch_status():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.db")
        store = StateStore(path)

        runner = DaemonRunner(
            tick_fn=lambda: None,
            state_store=store,
            sleep_fn=_no_sleep,
        )
        runner.run(max_iterations=1)

        ks = store.load_kill_switch()
        assert ks is not None
        assert ks["status"] == "STOPPED"
        assert ks["trip_reason"] == "daemon shutdown"

        store.close()


def test_state_store_saves_stats():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.db")
        store = StateStore(path)

        runner = DaemonRunner(
            tick_fn=lambda: None,
            state_store=store,
            sleep_fn=_no_sleep,
        )
        runner.run(max_iterations=2)

        stats = store.get("daemon_stats")
        assert stats is not None
        assert stats["iterations"] == 2
        assert stats["ticks_ok"] == 2

        store.close()


# ---------------------------------------------------------------------------
# stats() snapshot
# ---------------------------------------------------------------------------

def test_stats_returns_copy():
    runner = DaemonRunner(tick_fn=lambda: None, sleep_fn=_no_sleep)
    s1 = runner.stats()
    s1["iterations"] = 999
    s2 = runner.stats()
    assert s2["iterations"] == 0  # nao foi afetado