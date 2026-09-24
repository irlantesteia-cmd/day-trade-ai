"""
Persistencia de estado para operacao 24/7.

Armazena key-value JSON em SQLite (stdlib, sem dependencias novas).
Usado para:
  - Estado do KillSwitch (status, trip_reason, timestamp)
  - Snapshot de metricas (contadores relevantes)
  - Timestamp do ultimo tick bem-sucedido
  - Configuracao de retomada (symbol, mode)

Design:
  - Chave e string, valor e dict (serializado como JSON)
  - Toda escrita e commitada imediatamente (durabilidade > performance)
  - Schema criado na inicializacao (idempotente)
  - Nao usa SQLAlchemy (evita acoplamento com Base.metadata do projeto)
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_STATE_PATH = "data/daemon_state.db"


class StateStore:
    """
    Armazenamento de estado persistente (key-value JSON em SQLite).

    Uso:
        store = StateStore("data/state.db")
        store.set("kill_switch", {"status": "ARMED"})
        val = store.get("kill_switch")
        store.delete("kill_switch")
    """

    def __init__(self, path: str = DEFAULT_STATE_PATH):
        self.path = path
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Grava (ou substitui) o estado associado a `key`."""
        if not isinstance(key, str) or not key:
            raise ValueError("key deve ser string nao vazia")
        if not isinstance(value, dict):
            raise TypeError("value deve ser dict")

        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(value, default=str)

        self._conn.execute(
            """
            INSERT INTO state (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, payload, now),
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retorna o dict associado a `key`, ou None."""
        cursor = self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            logger.warning("Valor corrompido em state[%s], retornando None", key)
            return None

    def delete(self, key: str) -> None:
        self._conn.execute("DELETE FROM state WHERE key = ?", (key,))
        self._conn.commit()

    def list_keys(self) -> List[str]:
        cursor = self._conn.execute("SELECT key FROM state ORDER BY key")
        return [row[0] for row in cursor.fetchall()]

    def updated_at(self, key: str) -> Optional[str]:
        cursor = self._conn.execute(
            "SELECT updated_at FROM state WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Helpers de alto nivel (usados pelo DaemonRunner)
    # ------------------------------------------------------------------

    def save_kill_switch(self, status: str, trip_reason: Optional[str]) -> None:
        self.set("kill_switch", {
            "status": status,
            "trip_reason": trip_reason,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

    def load_kill_switch(self) -> Optional[Dict[str, Any]]:
        return self.get("kill_switch")

    def save_heartbeat(self, source: str) -> None:
        self.set("heartbeat", {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def load_heartbeat(self) -> Optional[Dict[str, Any]]:
        return self.get("heartbeat")

    def save_daemon_config(self, config: Dict[str, Any]) -> None:
        self.set("daemon_config", {
            **config,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        })

    def load_daemon_config(self) -> Optional[Dict[str, Any]]:
        return self.get("daemon_config")