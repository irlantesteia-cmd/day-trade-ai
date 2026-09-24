"""
Configuracao do ambiente Alembic.

Le DATABASE_URL de src.core.config.settings (fonte unica de verdade)
e registra Base.metadata de src.data.database para autogenerate.

Suporta SQLite (dev) e PostgreSQL (prod) sem alteracao.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Config do Alembic (lida de alembic.ini)
config = context.config

# Setup de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Importar Base + models (popula Base.metadata para autogenerate)
# ---------------------------------------------------------------------------
from src.core.config import settings  # noqa: E402
from src.data.database import Base  # noqa: E402
from src.data import models as _models  # noqa: E402, F401  (registra tabelas)

# Override URL a partir de Settings (nao usar o valor do alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()