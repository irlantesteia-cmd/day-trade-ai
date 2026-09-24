"""Testes do Scheduler (agendador de tarefas periodicas)."""
import pytest

from src.daemon.scheduler import Scheduler


def test_every_registers_task():
    sch = Scheduler()
    sch.every(10.0, "task1", lambda: None)
    assert "task1" in sch.names()


def test_every_invalid_interval_raises():
    sch = Scheduler()
    with pytest.raises(ValueError):
        sch.every(0, "task", lambda: None)
    with pytest.raises(ValueError):
        sch.every(-1.0, "task", lambda: None)


def test_every_empty_name_raises():
    sch = Scheduler()
    with pytest.raises(ValueError):
        sch.every(10.0, "", lambda: None)


def test_every_non_callable_raises():
    sch = Scheduler()
    with pytest.raises(TypeError):
        sch.every(10.0, "task", "not callable")


def test_first_tick_runs_all_tasks():
    sch = Scheduler()
    executed = []
    sch.every(10.0, "a", lambda: executed.append("a"))
    sch.every(20.0, "b", lambda: executed.append("b"))

    result = sch.tick(now=100.0)
    assert sorted(result) == ["a", "b"]
    assert sorted(executed) == ["a", "b"]


def test_task_not_run_before_interval():
    sch = Scheduler()
    executed = []
    sch.every(10.0, "a", lambda: executed.append("a"))

    sch.tick(now=100.0)  # primeira execucao
    executed.clear()

    # 5s depois: nao vencido
    result = sch.tick(now=105.0)
    assert result == []
    assert executed == []


def test_task_runs_after_interval():
    sch = Scheduler()
    executed = []
    sch.every(10.0, "a", lambda: executed.append("a"))

    sch.tick(now=100.0)
    executed.clear()

    # 10s depois: vencido
    result = sch.tick(now=110.0)
    assert result == ["a"]
    assert executed == ["a"]


def test_task_runs_more_than_interval():
    """Se o daemon dormiu demais, a tarefa roda mesmo assim."""
    sch = Scheduler()
    executed = []
    sch.every(10.0, "a", lambda: executed.append("a"))

    sch.tick(now=100.0)
    executed.clear()

    # 50s depois (bem mais que 10)
    result = sch.tick(now=150.0)
    assert result == ["a"]


def test_multiple_tasks_independent_intervals():
    sch = Scheduler()
    executed = []
    sch.every(1.0, "fast", lambda: executed.append("fast"))
    sch.every(10.0, "slow", lambda: executed.append("slow"))

    sch.tick(now=0.0)
    executed.clear()

    # +2s: so fast
    sch.tick(now=2.0)
    assert executed == ["fast"]
    executed.clear()

    # +11s: fast (intervalo 1) + slow (intervalo 10)
    sch.tick(now=11.0)
    assert sorted(executed) == ["fast", "slow"]


def test_task_exception_does_not_break_others():
    sch = Scheduler()
    executed = []

    def bad():
        raise RuntimeError("boom")

    sch.every(10.0, "bad", bad)
    sch.every(10.0, "good", lambda: executed.append("good"))

    result = sch.tick(now=100.0)
    assert "bad" in result
    assert "good" in result
    assert executed == ["good"]

    # A tarefa bad registrou o erro
    bad_task = sch.task("bad")
    assert bad_task.error_count == 1
    assert "boom" in bad_task.last_error


def test_run_count_and_error_count():
    sch = Scheduler()
    calls = []
    sch.every(5.0, "t", lambda: calls.append(1))

    sch.tick(now=0.0)
    sch.tick(now=5.0)
    sch.tick(now=10.0)

    assert sch.task("t").run_count == 3
    assert len(calls) == 3


def test_remove_task():
    sch = Scheduler()
    executed = []
    sch.every(10.0, "a", lambda: executed.append("a"))
    sch.remove("a")

    result = sch.tick(now=100.0)
    assert result == []
    assert executed == []


def test_remove_missing_silent():
    sch = Scheduler()
    sch.remove("nao_existe")  # nao deve levantar


def test_names_sorted():
    sch = Scheduler()
    sch.every(10.0, "z", lambda: None)
    sch.every(10.0, "a", lambda: None)
    sch.every(10.0, "m", lambda: None)
    assert sch.names() == ["a", "m", "z"]


def test_every_overwrites_existing():
    sch = Scheduler()
    sch.every(10.0, "t", lambda: None)
    sch.every(20.0, "t", lambda: None)
    assert sch.task("t").interval_sec == 20.0


def test_reset_clears_tasks():
    sch = Scheduler()
    sch.every(10.0, "a", lambda: None)
    sch.every(10.0, "b", lambda: None)
    sch.reset()
    assert sch.names() == []