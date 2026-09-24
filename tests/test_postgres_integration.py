"""
Testes de integracao com PostgreSQL.

Estrategia:
  - Testes que dependem de Postgres: skip individual via `skip_if_no_pg`
  - Testes estruturais (presenca de arquivos): rodam sempre
  - Auto-skip quando DATABASE_URL nao aponta para postgres

Isso permite rodar a suite normalmente em dev (SQLite) sem depender
de Postgres instalado, mas valida tudo quando ha um Postgres local
ou via docker-compose disponivel.

Uso local com Postgres:
    docker compose up -d db
    $env:DATABASE_URL = "postgresql+psycopg2://daytrade:daytrade@localhost:5432/daytrade"
    pytest tests/test_postgres_integration.py -v
"""
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _postgres_url() -> str:
    """Retorna a URL de Postgres configurada, ou vazia."""
    return os.getenv("DATABASE_URL", "")


def _is_postgres(url: str) -> bool:
    return url.startswith("postgresql") or url.startswith("postgres://")


skip_if_no_pg = pytest.mark.skipif(
    not _is_postgres(_postgres_url()),
    reason="DATABASE_URL nao aponta para Postgres (auto-skip em dev SQLite)",
)


# ---------------------------------------------------------------------------
# Fixtures (so usadas pelos testes que dependem de Postgres)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pg_engine():
    """Cria engine Postgres a partir de DATABASE_URL. Skip se nao conectar."""
    from sqlalchemy import create_engine, text

    url = _postgres_url()
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres indisponivel em {url}: {exc}")

    yield engine
    engine.dispose()


@pytest.fixture
def pg_session(pg_engine):
    """Sessao isolada contra Postgres. Faz rollback no final."""
    from sqlalchemy.orm import Session

    session = Session(bind=pg_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def schema(pg_engine):
    """Garante que as tabelas existam. Idempotente."""
    from src.data.database import Base
    from src.data import models as _models  # noqa: F401 (registra tabelas)
    Base.metadata.create_all(bind=pg_engine)
    yield


# ---------------------------------------------------------------------------
# Testes estruturais (rodam SEMPRE, sem Postgres)
# ---------------------------------------------------------------------------

def test_alembic_ini_exists():
    assert Path("alembic.ini").is_file()


def test_migrations_env_reads_settings():
    """env.py le DATABASE_URL de Settings (nao hardcoded)."""
    env_py = Path("migrations/env.py").read_text(encoding="utf-8")
    assert "from src.core.config import settings" in env_py
    assert "settings.DATABASE_URL" in env_py


def test_docker_compose_has_postgres_service():
    """docker-compose.yml tem servico postgres configurado."""
    content = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres" in content.lower()
    assert "pgdata" in content
    assert "5432:5432" in content


# ---------------------------------------------------------------------------
# Testes que dependem de Postgres (auto-skip se indisponivel)
# ---------------------------------------------------------------------------

@skip_if_no_pg
def test_postgres_version(pg_engine):
    """Postgres acessivel e versao >= 12."""
    from sqlalchemy import text

    with pg_engine.connect() as conn:
        version = conn.execute(text("SHOW server_version")).scalar()
    assert version is not None
    major = int(str(version).split(".")[0])
    assert major >= 12, f"Postgres >= 12 esperado, obtido {version}"


@skip_if_no_pg
def test_candles_table_created(schema, pg_engine):
    """Tabela candles existe apos create_all."""
    from sqlalchemy import inspect

    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    assert "candles" in tables


@skip_if_no_pg
def test_insert_and_read_candle(pg_session, schema):
    """Insert + read de Candle via CandleRepository."""
    from src.data.repository import CandleRepository
    from src.domain.enums import Timeframe
    from src.domain.models import Candle

    repo = CandleRepository(pg_session)

    candle = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
        volume=1500.0,
    )

    n = repo.save_candles([candle])
    assert n == 1

    pg_session.flush()

    candles = repo.get_candles("WIN", Timeframe.M1)
    assert len(candles) >= 1
    found = [c for c in candles if c.timestamp == candle.timestamp]
    assert len(found) == 1
    assert found[0].close == 104.0


@skip_if_no_pg
def test_bulk_insert(pg_session, schema):
    """Insercao em lote funciona."""
    from src.data.repository import CandleRepository
    from src.domain.enums import Timeframe
    from src.domain.models import Candle

    repo = CandleRepository(pg_session)

    candles = [
        Candle(
            symbol="BULK",
            timeframe=Timeframe.M5,
            timestamp=datetime(2026, 1, 1, 10, i, 0, tzinfo=timezone.utc),
            open=100.0 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.5 + i,
            volume=1000.0 + i,
        )
        for i in range(10)
    ]

    n = repo.save_candles(candles)
    assert n == 10

    pg_session.flush()

    result = repo.get_candles("BULK", Timeframe.M5)
    assert len(result) == 10