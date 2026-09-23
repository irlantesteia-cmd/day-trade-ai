# ADR-007 - Renomear PortfolioManager de execution para AccountState

- **Status**: Aceito
- **Data**: 2026-09-23

## Contexto

Existiam duas classes com o mesmo nome `PortfolioManager`, mas com
responsabilidades distintas:

- `src/execution/portfolio.py::PortfolioManager`
    - Estado financeiro da conta durante execucao
    - Campos: `cash`, `balance`, `equity` (property), `positions`
    - Metodos: `deposit`, `withdraw`, `add_position`, `remove_position`,
      `update_positions_pnl`
    - Consumidores: `src/execution/engine.py` (1 arquivo)

- `src/portfolio/manager.py::PortfolioManager`
    - Alocacao de capital entre multiplos ativos
    - Campos: `total_capital`, `max_asset_weight`
    - Metodos: `allocate_equal_weight`, `allocate_custom_weights`
    - Consumidores: `tests/test_portfolio.py`, `tests/test_rebalancer.py`,
      exportado via `src/portfolio/__init__.py`
    - Conceito correto para o nome "Portfolio"

Nao havia colisao direta de import hoje, mas o nome duplicado e confuso
e pode causar bugs em refatoracoes futuras.

## Decisao

Renomear **apenas** o `PortfolioManager` de `execution` para `AccountState`.

Escolha do nome:
- `AccountState` descreve exatamente o que a classe modela
- Alinha com nomenclatura de mercado (account state vs portfolio allocation)
- Nao conflita com nenhum outro nome no projeto

### Mudancas

1. `src/execution/portfolio.py`:
   - Classe `PortfolioManager` renomeada para `AccountState`
   - Docstring ASCII explicando a distincao com o outro PortfolioManager
   - Alias `PortfolioManager = AccountState` mantido no final do arquivo
     (deprecado, sera removido em milestone futuro)

2. `src/execution/engine.py`:
   - Import atualizado para `AccountState`
   - Construtor instancia `AccountState(initial_balance=...)`
   - Parametro `portfolio=None` mantido (nome historico do argumento)

## Consequencias

- Dois conceitos com nomes distintos ✅
- Compatibilidade retroativa via alias ✅
- 164 testes passando ✅
- Nenhum consumidor externo quebrado ✅

## Alternativas descartadas

- **Renomear o `src/portfolio/manager.py::PortfolioManager`**: rejeitada
  porque o nome "Portfolio" esta semanticamente correto para alocacao de
  capital, e a classe e consumida por mais arquivos (incluindo `__init__.py`).
- **Deletar um dos dois**: rejeitada porque ambos servem propositos legitimos
  e diferentes.
- **Manter ambos sem rename**: rejeitada por violar clareza e dificultar
  manutencao futura.

## Estado residual (backlog)

- Alias `PortfolioManager = AccountState` deve ser removido apos confirmar
  que nenhum codigo externo o usa. Registrado em `docs/roadmap.md`.
- Nome do parametro `portfolio` no `ExecutionEngine.__init__` continua
  historico. Pode ser renomeado para `account_state` em milestone futuro.