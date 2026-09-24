# ADR-011 - PostgreSQL e migrations com Alembic

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

Antes deste milestone:
- `src/data/database.py` ja usava SQLAlchemy 2.0 com engine configurada
  via `settings.DATABASE_URL`.
- O SQLite de desenvolvimento (`daytrade.db`) era criado implicitamente
  pelo SQLAlchemy na primeira operacao (via `Base.metadata.create_all`,
  ou simplesmente nao criado ate uma insercao).
- Nao havia versionamento de schema.
- Alteracoes em `src/data/models.py` nao eram propagadas automaticamente
  para bancos existentes.
- PostgreSQL nao estava declarado nem instalado.

A FASE 18 (Production) do framework requer PostgreSQL + ORM (SQLAlchemy)
+ migracoes (implicito).

## Decisao

Adicionar suporte a PostgreSQL e versionamento de schema via **Alembic**,
mantendo SQLite como padrao em dev.

### Mudancas

**1. `pyproject.toml`**
- `sqlalchemy>=2.0` movido para `dependencies` (ja era instalado, agora
  declarado explicitamente).
- Novo extra `[postgres]`: `alembic>=1.13`, `psycopg2-binary>=2.9`.
- Extra `[dev]` ganha `alembic>=1.13` (testar migracoes sem Postgres).

**2. Estrutura Alembic**
- `alembic.ini` (gerado por `alembic init`)
- `migrations/env.py` adaptado:
  - Importa `Base` de `src.data.database` e `models` de `src.data`
    (para popular metadata)
  - Le `DATABASE_URL` de `src.core.config.settings`
  - `compare_type=True` (detecta mudancas de tipo)
- `migrations/versions/6424d1840b79_initial_schema_candles.py`
  (autogenerate da tabela `candles` + 3 indices)

**3. `tests/test_migrations.py`**
- 5 testes de sanidade:
  - `migrations/` e `alembic.ini` existem
  - Ao menos uma revision em `migrations/versions/`
  - Tabela `candles` existe no SQLite apos `alembic upgrade head`
  - Revision contem `create_table("candles", ...)`
- Auto-skip se o banco nao foi migrado (ambiente limpo)

## Uso

```powershell
# Instalar extras
pip install -e ".[postgres,dev]"

# Aplicar migrations
alembic upgrade head

# Ver revision atual
alembic current

# Criar nova migration apos alterar models
alembic revision --autogenerate -m "descricao"

# Rollback
alembic downgrade -1

Compatibilidade
SQLite continua sendo o padrao em .env.example (DATABASE_URL=sqlite:///./daytrade.db).

PostgreSQL funciona mudando DATABASE_URL:
postgresql+psycopg2://user:pass@host:5432/daytrade.

Todo o codigo existente (CandleRepository, SessionLocal, Base)
permanece inalterado.

189 testes passando (eram 184; +5).

Nao coberto (backlog da FASE 18)
database.py com side effect em import: create_engine() roda ao
importar o modulo. Idealmente a engine seria lazy (factory). Manter
como esta por enquanto para nao quebrar 4 consumidores. Registrado no
roadmap.

Docker Compose com Postgres: nenhum servico postgres adicionado
em docker-compose.yml (fica para milestone de deploy real).

Dados seed: nenhuma migration popula dados iniciais.

Teste em Postgres real: os testes rodam contra SQLite. Nenhum teste
e executado contra um Postgres efetivo em CI (configuravel via
DATABASE_URL futuro).

Backup / restore: nao implementado.

alembic.ini nao contem URL real: a URL e injetada por env.py
a partir de Settings. Se alguem rodar alembic sem o pacote
instalado (pip install -e .), vai falhar ao importar src.

Alternativas descartadas
Manter apenas SQLite: rejeitada por nao escalar para producao.

Base.metadata.create_all() em vez de Alembic: rejeitada por
nao versionar mudancas e nao permitir rollback.

Alembic com URL hard-coded em alembic.ini: rejeitada por
duplicar config (violaria ADR-002).

Flyway / Django migrations / outro framework: rejeitada por
escolher algo fora do ecossistema SQLAlchemy.

