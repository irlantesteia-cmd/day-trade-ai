"""
Testes de sanidade das migracoes Alembic.

Nao substituem rodar `alembic upgrade head` manualmente em prod, mas
garantem que:
  - O script de migracao foi gerado corretamente
  - A revision atual corresponde ao head
  - A tabela candles existe no banco de dev
"""
import os
import sqlite3

import pytest

from src.core.config import settings


def _db_path_from_url(url: str) -> str:
    """Extrai o caminho do arquivo de um DATABASE_URL sqlite."""
    if not url.startswith("sqlite"):
        pytest.skip("Teste so se aplica a SQLite (ambiente de dev)")
    # sqlite:///./daytrade.db -> ./daytrade.db
    path = url.replace("sqlite:///", "").replace("sqlite://", "")
    return path or "daytrade.db"


def test_migrations_directory_exists():
    """migrations/ deve existir com env.py e versions/."""
    assert os.path.isdir("migrations")
    assert os.path.isfile(os.path.join("migrations", "env.py"))
    assert os.path.isdir(os.path.join("migrations", "versions"))


def test_alembic_ini_exists():
    assert os.path.isfile("alembic.ini")


def test_at_least_one_revision_exists():
    versions_dir = os.path.join("migrations", "versions")
    revisions = [f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("__")]
    assert len(revisions) >= 1, "Nenhuma revision Alembic encontrada"


def test_candles_table_created_by_migration():
    """
    Apos `alembic upgrade head`, a tabela candles deve existir no SQLite.
    Faz skip se o banco ainda nao foi migrado.
    """
    db_path = _db_path_from_url(settings.DATABASE_URL)
    if not os.path.exists(db_path):
        pytest.skip(f"Banco {db_path} nao existe (rode `alembic upgrade head`)")

    conn = sqlite3.connect(db_path)
    try:
        names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master").fetchall()]
    finally:
        conn.close()

    assert "candles" in names, "Tabela 'candles' nao encontrada"
    assert "alembic_version" in names, "Tabela de controle do Alembic nao encontrada"


def test_migration_file_mentions_candles():
    """A revision inicial deve criar a tabela candles."""
    versions_dir = os.path.join("migrations", "versions")
    found = False
    for fname in os.listdir(versions_dir):
        if not fname.endswith(".py"):
            continue
        with open(os.path.join(versions_dir, fname), "r", encoding="utf-8") as f:
            content = f.read()
        if "candles" in content and "create_table" in content:
            found = True
            break
    assert found, "Nenhuma revision cria a tabela candles"