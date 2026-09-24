# ADR-017 - Dashboard HTML estatico

- **Status**: Aceito
- **Data**: 2026-09-24

## Contexto

A FASE 16 (API HTTP) foi concluida em M5 (ADR-009), com 6 endpoints
expostos via FastAPI. A FASE 17 (Dashboard, secao 42 do framework)
previa uma interface visual para monitoramento.

Nao havia:
- Templates/HTML em `src/api/`
- Diretorio `static/`
- Nenhuma dependencia de frontend declarada

## Decisao

Implementar dashboard como **HTML+JS estatico** servido pelo proprio
FastAPI em `GET /`, sem framework frontend e sem novas dependencias.

### Justificativa (framework secao 61)

- **Nao adicionar tecnologia so porque e popular**: React/Vue/Streamlit
  nao tem uso concreto comprovado neste milestone.
- **Zero dependencias novas**: FastAPI ja serve HTML (`HTMLResponse`).
- **Zero processos extras**: nao precisa rodar Streamlit separado.
- **Frontend separado por design**: HTML puro + fetch aos endpoints
  existentes. Nao contem logica critica de risco (secao 42 respeitada).
- **Extensivel**: se Streamlit for util depois, o backend continua o
  mesmo.

### Estrutura
src/api/
├── http.py (adiciona endpoint GET / e STATIC_DIR)
└── static/
└── index.html (dashboard, ~3.6 KB, zero deps externas)


### Dashboard (index.html)

- **Auto-refresh**: `setInterval(refresh, 5000)` — atualiza a cada 5s
- **Fetch endpoints**:
  - `GET /status`    -> estado do sistema
  - `GET /health`    -> saude dos componentes
  - `GET /metrics`   -> contadores e latencias
  - `GET /performance` -> relatorio executivo
- **Botoes de acao**:
  - Start Paper -> `POST /paper/start`
  - Stop Paper  -> `POST /paper/stop`
- **Tratamento de erro**: bloco de erro em vermelho; sucesso em verde
- **Sem frameworks JS**: vanilla JS, ~50 linhas

### Endpoint `/` no FastAPI

```python
@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="dashboard nao encontrado")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))

Le o HTML do disco a cada request. Simples e suficiente para ~3.6 KB.

Cobertura de testes
tests/test_api_http.py (+3 testes):

test_dashboard_returns_html: GET / retorna 200 com text/html

test_dashboard_contains_title_and_sections: contem titulo e secoes

test_dashboard_references_api_endpoints: JS aponta para todos os
endpoints consumidos

Suite total: 221 passed (eram 218; +3).

Como usar
# Iniciar servidor
uvicorn src.api.http:app --reload

# Abrir no navegador
# http://127.0.0.1:8000/

Nao coberto (backlog)
Graficos / charts: sem plotly, sem D3. Tabelas + JSON cru.

Streaming (WebSocket): o dashboard usa polling a cada 5s.

Autenticacao: nenhuma. Se expuser publicamente, obrigatorio.

Historico de eventos: /events nao existe. Seria util agora que
o EventBus existe (M12) — backlog.

Filtros, busca, dark mode: cosmético.

Build/minificacao: HTML puro servido em runtime, sem bundler.

Multi-usuario / sessoes: sem estado no cliente.

Mobile-first: layout responsivo basico (max-width + viewport).

Consequencias
Dashboard funcional em http://host:porta/ ✅

Zero dependencias novas ✅

Frontend separado (respeita secao 42) ✅

3 testes de integracao ✅

221 testes passando (eram 218; +3)

Base extensivel para graficos/streaming em milestones futuros

Alternativas descartadas
Streamlit: rejeitada por adicionar dependencia pesada e exigir
processo separado (nao roda embutido no FastAPI).

React / Vue: rejeitada por complexidade desproporcional ao escopo.
Bundler + npm + build pipeline para 3.6 KB de HTML nao se justifica.

Jinja2 com templates server-side: rejeitada por introduzir
dependencia desnecessaria. HTML estatico + fetch e suficiente.

Adicionar plotly imediatamente: rejeitada por Regra n. 1
(nao construir tudo de uma vez). Graficos ficam para milestone futuro.
