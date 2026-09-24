# ADR-009 - API HTTP com FastAPI

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

O `APIGateway` existente (`src/api/app.py`) expunha 3 metodos Python:

- `get_health() -> Dict`
- `get_metrics() -> Dict`
- `get_performance_report(format_type) -> Dict`

Nao havia servidor HTTP. Clientes externos (dashboard, monitoramento,
automacao) nao conseguiam consumir o sistema.

A secao 41 do framework define endpoints HTTP esperados.

## Decisao

Adicionar uma **camada HTTP fina** sobre o `APIGateway` existente,
preservando o contrato Python original.

### Arquitetura
Cliente HTTP
|
v
FastAPI (src/api/http.py)
|
v
APIGateway (src/api/app.py) <- preservado, sem alteracao
|
v
build_system() -> LiveTradingEngine, MetricsCollector, etc

### Mudancas

**1. `pyproject.toml`**
- Novo extra `[api]`: `fastapi>=0.110`, `uvicorn[standard]>=0.27`, `httpx>=0.27`
- Extra `[dev]` ganha `httpx>=0.27` (para tests com TestClient)

**2. `src/api/http.py` (novo)**
- Instancia `FastAPI` com titulo e descricao
- Gateway lazy: `app.state.gateway` e criado na primeira requisicao
- Funcao `set_gateway()` para injecao em testes (evita `build_system` em cada request)
- Endpoints implementados:
  - `GET  /health`       -> `gateway.get_health()`
  - `GET  /metrics`      -> `gateway.get_metrics()`
  - `GET  /status`       -> resumo (environment, trading_mode, engine_running, kill_switch)
  - `GET  /performance`  -> `gateway.get_performance_report(format=json|markdown)`
  - `POST /paper/start`  -> `engine.start()` (idempotente)
  - `POST /paper/stop`   -> `engine.stop()` (idempotente)
- Tratamento de erro: 500 com `HTTPException` + log de excecao
- Validacao de query: `format` aceita apenas `json|markdown` (422 caso contrario)
- Entry point: `python -m src.api.http` roda uvicorn em `127.0.0.1:8000`

**3. `tests/test_api_http.py` (novo)**
- 10 testes usando `TestClient` do FastAPI
- Fixture `client` injeta `APIGateway` real e evita rebuild
- Cobre: health, metrics, status, performance json/markdown/invalid,
  paper start/stop, idempotencia, openapi schema

### Nao alterado

- `APIGateway` em `src/api/app.py` permanece intacto
- `tests/test_api.py` (4 testes legado) continua passando
- `src/api/__init__.py` nao exporta `http` (importacao explicita:
  `from src.api.http import app`)

## Consequencias

- API HTTP funcional ✅
- 10 testes novos ✅
- Suite total: 177 passed (eram 167)
- Contrato Python original preservado ✅
- Documentacao interativa auto-gerada em `/docs` (Swagger) e `/redoc`
- Schema OpenAPI em `/openapi.json`

## Nao coberto (milestones futuros)

- **Autenticacao**: sem API key, sem OAuth. Se expor publicamente,
  obrigatorio.
- **Endpoints de estrategia**: `/strategies`, `/strategies/{id}/enable`,
  `/strategies/{id}/disable` (framework secao 41).
- **Endpoints de dados**: `/signals`, `/positions`, `/orders`,
  `/portfolio`, `/risk`, `/market`.
- **Endpoints de acao**: `/backtest`.
- **WebSocket / streaming**: nenhum.
- **Rate limiting**: nenhum.
- **HTTPS**: responsabilidade do reverse proxy (nginx/caddy) em producao.
- **Docker**: container precisa expor porta 8000.
- **`uvicorn` production tuning**: workers, `--limit-concurrency`, etc.

Registrar esses itens em `docs/roadmap.md` como backlog da PHASE 16.

## Alternativas descartadas

- **Substituir APIGateway por FastAPI**: rejeitada. Quebraria
  `tests/test_api.py` e outros consumidores programaticos. Preferimos
  camada adicional.
- **Usar Flask em vez de FastAPI**: rejeitada. FastAPI tem async nativo,
  validacao Pydantic, OpenAPI automatico.
- **Implementar autenticacao basica agora**: rejeitada por escopo.
  Fica para milestone dedicado antes de qualquer exposicao publica.
- **Adicionar todos os endpoints da secao 41 de uma vez**: rejeitada
  pela Regra n. 1 (nao construir tudo de uma vez). Comecamos com
  endpoints de leitura + controle de paper.