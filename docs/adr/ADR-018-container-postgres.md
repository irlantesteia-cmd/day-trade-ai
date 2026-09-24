# ADR-018 - Container Postgres e testes de integracao

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O ADR-011 (M7) adicionou PostgreSQL + Alembic como caminho de producao,
mas o ambiente de desenvolvimento continuava sem um servico Postgres
disponivel. O docker-compose tinha apenas o servico `app`.

Consequencias:
- Testes so rodavam contra SQLite
- Nenhuma validacao real do caminho Postgres
- Onboarding de novo dev exigia instalar Postgres manualmente

## Decisao

Adicionar servico `db` (Postgres 16-alpine) ao docker-compose e testes
de integracao que auto-skipam quando Postgres nao esta disponivel.

### Mudancas

**1. `docker-compose.yml`**

Novo servico `db`:
- Imagem: `postgres:16-alpine`
- Volume nomeado `pgdata` (persistencia)
- Porta 5432 exposta para dev local
- Healthcheck com `pg_isready` (interval 5s, retries 10)
- Credenciais padrao dev: `daytrade:daytrade` no db `daytrade`

App:
- `depends_on.db.condition: service_healthy` (so sobe apos db pronto)
- `DATABASE_URL` aponta para `postgresql+psycopg2://daytrade:daytrade@db:5432/daytrade`

**2. `Dockerfile`**

- `libpq-dev` no apt (garante build do psycopg2 se necessario)
- `pip install ".[api,postgres]"` (FastAPI + Uvicorn + Alembic + psycopg2)
- Copia `migrations/` e `alembic.ini` para rodar migracoes no container
- `CMD` roda `uvicorn src.api.http:app` (era `python -m src.main`)

**3. `.env.example`**

`DATABASE_URL` comentado com 3 opcoes:
- SQLite (default, dev local)
- Postgres local (`localhost:5432`)
- Postgres docker-compose (`db:5432`)

**4. `tests/test_postgres_integration.py`** (novo)

Estrategia hibrida:
- **3 testes estruturais** rodam SEMPRE (sem Postgres):
  - `alembic.ini` existe
  - `migrations/env.py` le `settings.DATABASE_URL` (nao hardcoded)
  - `docker-compose.yml` tem servico postgres + volume + porta
- **4 testes de integracao** auto-skipam se `DATABASE_URL` nao for
  postgres ou se Postgres nao conectar:
  - Versao >= 12
  - Tabela `candles` criada
  - Insert + read de `Candle` via `CandleRepository`
  - Bulk insert de 10 candles

Skip individual via `pytest.mark.skipif` (nao global), permitindo que
testes estruturais rodem em qualquer ambiente.

## Como usar

### Dev local com Postgres via Docker

```powershell
# Subir apenas o banco
docker compose up -d db

# Apontar DATABASE_URL para o Postgres local
$env:DATABASE_URL = "postgresql+psycopg2://daytrade:daytrade@localhost:5432/daytrade"

# Rodar migracoes
alembic upgrade head

# Rodar testes de integracao
pytest tests/test_postgres_integration.py -v

Dev local sem Postgres (default)
# SQLite permanece default (DATABASE_URL=sqlite:///./daytrade.db)
pytest tests/ -q
# -> 224 passed, 4 skipped

Stack completa (app + db)
docker compose up -d
# App em http://localhost:8000
# Postgres em localhost:5432

Consequencias
Postgres disponivel via docker-compose ✅

Testes de integracao prontos, auto-skip sem Postgres ✅

Dockerfile instala extras [api,postgres] ✅

.env.example documenta 3 opcoes de DATABASE_URL ✅

224 passed, 4 skipped (eram 221; +3 estruturais +4 skip) ✅

Onboarding simplificado ✅

Nao coberto (backlog)
Docker nao instalado no ambiente dev atual: usuario precisa
instalar Docker Desktop para rodar os testes de integracao. Documentar
no README fica para milestone futuro.

CI sem Postgres: o .github/workflows/ci.yml roda apenas SQLite.
Adicionar services.postgres no workflow e rodar os testes de
integracao em CI fica para milestone futuro.

Migracao automatica no container: o CMD nao roda
alembic upgrade head antes do uvicorn. Producao precisa de entrypoint
que faca isso (ou orquestrador externo).

Secrets: credenciais daytrade:daytrade sao de dev. Producao
precisa de secrets management (Vault, AWS Secrets Manager, etc.).

Backup/restore: nao implementado.

Alternativas descartadas
Instalar Postgres nativo no Windows: rejeitada por complexidade
de setup e por fugir do padrao Docker usado em producao.

Usar sqlite em memoria para testes: rejeitada. SQLite nao valida
tipos, constraints, indices nem comportamento do Postgres.

Testcontainers (biblioteca Python): rejeitada por adicionar
dependencia pesada (docker SDK) e por exigir Docker igualmente.

Skip global (pytestmark) nos testes de integracao: rejeitada
porque impede testes estruturais de rodar sem Postgres.