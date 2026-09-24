"""Testes do StateStore (persistencia de estado do daemon)."""
import os
import tempfile

import pytest

from src.daemon.state import StateStore


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.db")
        s = StateStore(path)
        yield s
        s.close()


def test_set_and_get(store):
    store.set("k", {"a": 1})
    assert store.get("k") == {"a": 1}


def test_get_missing_returns_none(store):
    assert store.get("nao_existe") is None


def test_update_overwrites(store):
    store.set("k", {"a": 1})
    store.set("k", {"a": 2, "b": 3})
    assert store.get("k") == {"a": 2, "b": 3}


def test_delete(store):
    store.set("k", {"a": 1})
    store.delete("k")
    assert store.get("k") is None


def test_list_keys(store):
    store.set("b", {"x": 1})
    store.set("a", {"y": 2})
    store.set("c", {"z": 3})
    assert store.list_keys() == ["a", "b", "c"]


def test_updated_at(store):
    store.set("k", {"a": 1})
    ts = store.updated_at("k")
    assert ts is not None
    assert "T" in ts  # ISO format


def test_empty_key_raises(store):
    with pytest.raises(ValueError):
        store.set("", {"a": 1})


def test_non_dict_value_raises(store):
    with pytest.raises(TypeError):
        store.set("k", "not a dict")
    with pytest.raises(TypeError):
        store.set("k", [1, 2, 3])


def test_persistence_across_reopen():
    """Estado persiste entre fechar e reabrir o store."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "state.db")

        s1 = StateStore(path)
        s1.set("k", {"value": 42})
        s1.close()

        s2 = StateStore(path)
        assert s2.get("k") == {"value": 42}
        s2.close()


def test_save_and_load_kill_switch(store):
    store.save_kill_switch("TRIPPED", "max daily loss")
    data = store.load_kill_switch()
    assert data is not None
    assert data["status"] == "TRIPPED"
    assert data["trip_reason"] == "max daily loss"
    assert "saved_at" in data


def test_save_and_load_heartbeat(store):
    store.save_heartbeat("daemon_loop")
    data = store.load_heartbeat()
    assert data is not None
    assert data["source"] == "daemon_loop"
    assert "timestamp" in data


def test_save_and_load_daemon_config(store):
    store.save_daemon_config({
        "symbol": "WINV26",
        "mode": "paper_mt5",
        "poll_interval": 5.0,
    })
    data = store.load_daemon_config()
    assert data is not None
    assert data["symbol"] == "WINV26"
    assert data["mode"] == "paper_mt5"
    assert data["poll_interval"] == 5.0
    assert "saved_at" in data


def test_value_serialization_complex_types(store):
    """Tipos não-nativos viram string via json default=str."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    store.set("k", {"timestamp": now, "nested": {"list": [1, 2, 3]}})
    data = store.get("k")
    assert data is not None
    assert isinstance(data["timestamp"], str)
    assert data["nested"]["list"] == [1, 2, 3]