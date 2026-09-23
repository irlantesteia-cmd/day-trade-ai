# ADR-001 - Stack tecnologica

- **Status**: Aceito
- **Data**: 2026-09-22

## Contexto

Projeto precisa de linguagem com ecossistema maduro para analise quantitativa,
integracao com MetaTrader 5, machine learning classico e testes automatizados.

## Decisao

| Camada | Tecnologia | Justificativa |
|---|---|---|
| Linguagem | Python 3.12 | Ecossistema quant + MT5 oficial |
| Testes | pytest | Padrao da industria |
| Config | pydantic-settings | Validacao tipada + `.env` |
| Modelagem | dataclasses + pydantic | Leveza + validacao |
| Numerico | numpy | Vetorizacao |
| Serializacao ML | joblib | Eficiente para arrays numpy |
| Banco (dev) | SQLite | Zero setup |
| Banco (prod) | PostgreSQL | Escala futura |
| ORM | SQLAlchemy | (planejado) |
| API futura | FastAPI | (planejado) |
| CI | GitHub Actions | Integrado ao GitHub |
| Container | Docker | Deploy reproduzivel |

## MetaTrader 5 como dependencia opcional

**Problema:** `MetaTrader5` nao tem wheel para Linux. O CI roda em
`ubuntu-latest`.

**Solucao:** declarar em `[project.optional-dependencies].mt5`. O codigo
detecta ausencia via `HAS_MT5=False` e opera em modo mock.

## Consequencias

- Desenvolvimento em Windows e recomendado (para MT5 real)
- CI valida apenas o nucleo (sem MT5)
- FASE 19 (Broker Abstraction) permitira implementacoes alternativas

## Alternativas descartadas

- **TypeScript/Node**: ecossistema quant inferior
- **C++/Rust**: custo de desenvolvimento alto, prototipagem lenta
- **R**: menos integracao com infraestrutura moderna