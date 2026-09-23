# ADR-000 - Bootstrap do projeto

- **Status**: Aceito
- **Data**: 2026-09-22
- **Contexto**: Projeto construido incrementalmente via prompts e commits,
  sem framework formal de governanca ate agora.

## Contexto

A plataforma foi desenvolvida de forma iterativa, com decisoes tomadas caso a
caso. O roadmap oficial (PHASES 0-20) foi definido externamente e serve como
referencia. Antes deste ADR, nao havia documentacao formal de decisoes
arquiteturais nem registro de estado real das fases.

## Decisao

Adotar a partir de agora:

1. **Roadmap oficial de PHASES 0-20** como referencia de progresso
2. **Definition of Done**: codigo + testes + integracao + validacao + logs +
   documentacao + git
3. **ADRs** para decisoes arquiteturais significativas
4. **CHANGELOG** para rastreabilidade de mudancas
5. **Documentacao viva** em `docs/`

## Estado real no momento do ADR

- PHASES 1-13: [OK] concluidas
- PHASE 14 (ML): [~] parcial (modelo sem edge estatistico comprovado)
- PHASE 15 (Portfolio): [OK] concluida
- PHASE 16 (API): [~] parcial (classes Python, nao HTTP)
- PHASES 17-20: [ ] pendentes

## Consequencias

- Commits passam a seguir Conventional Commits
- Todo milestone gera ADR se houver decisao arquitetural
- Nao avancar de fase sem Definition of Done completa
- Estado do repositorio (git) passa a ser fonte de verdade

## Alternativas descartadas

- **Continuar sem documentacao**: rejeitada por risco de regressoes
  (ex: commits `DeepSeek` e `hsbvdhw` introduziram regressoes sem rastreio)
- **Documentar so no final**: rejeitada por violar o principio de evolucao
  incremental controlada