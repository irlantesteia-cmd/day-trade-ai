# Changelog

Todas as mudanças notáveis neste projeto são documentadas neste arquivo.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [Unreleased]

### Added
- Documentação: `docs/architecture.md`, `docs/development.md`, `docs/roadmap.md`, `docs/api.md`
- ADRs: `ADR-000-bootstrap`, `ADR-001-stack`, `ADR-002-config-duplication`
- `CHANGELOG.md` (este arquivo)

### Changed
- `README.md` expandido com instalação, uso, estrutura e princípios
- `pyproject.toml` — dependências reais declaradas (pydantic, pydantic-settings,
  numpy, joblib) + extras opcionais `[mt5]` e `[dev]`

### Fixed
- Regressões introduzidas no commit `9d9ac28` (DeepSeek):
  - `src/cli/runner.py`: default do argparse restaurado para `paper`
  - `src/main.py`: removido `engine.stop()` indevido em `run_app()`
- Código fora do framework removido (orquestrador multi-ativo, risk_parity,
  multi_market_adapter, multi_tf_strategy, train_multi_asset)

### Removed
- `src/orchestrator/` (reconstruir em PHASE 15)
- `src/strategies/multi_tf_strategy.py`
- `src/adapters/multi_market_adapter.py`
- `src/portfolio/risk_parity.py`
- `scripts/train_multi_asset.py`
- `models/multi/`

---

## [1.0.0] - 2026-09-22

### Added
- Certificação de release v1.0.0 com `RELEASE_NOTES.md`
- Pipeline de CI no GitHub Actions
- Orquestrador de deploy (`src/deploy/orchestrator.py`)
- Testes de certificação (`tests/test_final_release.py`, `tests/test_release_version.py`)

### Status das Fases
- PHASES 1–13 concluídas
- PHASE 14 (ML) parcial
- PHASE 15 (Portfolio) completa
- PHASE 16 (API) parcial
- FASES 17–20 pendentes

---

## Notas

- O projeto **não segue** SemVer estritamente nos commits internos.
  Para releases oficiais, criar tag no Git.
- Commits com mensagens pouco descritivas (`hsbvdhw`, `DeepSeek`) existem
  no histórico — recomenda-se evitar no futuro.