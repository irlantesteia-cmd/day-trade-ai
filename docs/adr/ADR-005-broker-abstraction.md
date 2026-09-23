# ADR-005 - Interface Broker (abstracao de execucao)

- **Status**: Aceito
- **Data**: 2026-09-23

## Contexto

O pipeline de execucao tinha tres implementacoes de broker com assinaturas
incompativeis:

- `PaperBroker.execute_order(order, current_price) -> Order`
- `MT5Adapter.execute_signal(signal, bar) -> Order`
- `MT5ExecutionEngine.execute_signal(signal, bar) -> Order` (wrapper)

Nao havia contrato formal. Cada broker tinha sua propria assinatura, o que
impedia:
  - Substituir um broker por outro sem refatorar quem chama
  - Testar o pipeline com broker mockado de forma padronizada
  - Documentar o que significa "ser um broker" neste sistema

## Decisao

Introduzir uma classe ABC `Broker` em `src/execution/broker_base.py`
com um unico metodo abstrato:

```python
class Broker(ABC):
    @abstractmethod
    def execute_order(self, order: Order, current_price: float) -> Order:
        ...

Implementacoes
PaperBroker herda de Broker (mudanca minima: class PaperBroker(Broker))

Ja tinha execute_order com assinatura compativel

Zero alteracao de comportamento

MT5Adapter adiciona execute_order(order, current_price) -> Order

Novo metodo, simetrico ao PaperBroker

execute_signal(signal, bar) mantido para compatibilidade

Se order ja tem SL/TP: usa-os

Se nao tem: calcula via SLTPCalculator (usa _signal_from_order como shim)

Nao herda de Broker (ver Alternativas)

Cobertura de testes
tests/test_broker_interface.py cobre:

Broker ABC nao pode ser instanciado

PaperBroker e subclass de Broker

PaperBroker.execute_order funciona via interface

MT5Adapter tem execute_order callable

Assinaturas de PaperBroker.execute_order e MT5Adapter.execute_order
sao identicas (self, order, current_price)

MT5Adapter.execute_order retorna a Order com status FILLED

MT5Adapter.execute_order calcula SL/TP quando ausentes

MT5Adapter.execute_order rejeita se desconectado

Total: 8 testes novos. Suite completa: 161 passed.

Fora de escopo (milestones futuros)
Este ADR nao corrige:

Duplicacao engine.py / executor.py: ambos definem ExecutionEngine
com o mesmo metodo process_order. Consolidar fica para milestone de
cleanup.

P3.c (RiskEngine nao integrado): LiveTradingEngine continua chamando
execution_engine.execute_signal(signal, bar) diretamente, sem passar por
RiskEngine.generate_order(). Refatorar isso exige mexer em 3 modulos ao
mesmo tempo.

MT5Adapter nao herda de Broker: ver Alternativas abaixo.

Unificar PortfolioManager: existem dois com propósitos diferentes
(src/execution/portfolio.py cash/balance, src/portfolio/manager.py
asset allocation). Nao conflitam hoje, mas o nome duplicado e confuso.

Alternativas descartadas
MT5Adapter herdar de Broker: rejeitada. Broker define
execute_order(order, price). MT5Adapter tambem precisa de
execute_signal(signal, bar) para uso legado em LiveTradingEngine. Se
ela herdasse, precisaria implementar os 2 metodos (1 abstrato + 1 extra),
o que quebraria a simetria com PaperBroker (que so tem execute_order).
Preferimos conformidade estrutural (assinatura identica) sem heranca.

Definir is_connected no ABC: rejeitada. PaperBroker nao tem
conceito de conexao. Forcar o atributo poluiria a interface por conveniencia
de um unico implementador.

Adicionar execute_signal tambem ao ABC: rejeitada. execute_signal
opera no nivel de Signal (camada Strategy), execute_order opera no nivel
de Order (camada Execution). Sao niveis diferentes. O ABC correto e
execute_order.

Refatorar MT5ExecutionEngine para receber Broker no construtor:
adiada. Faria parte de P3.c e mexeria em LiveTradingEngine, com risco de
regressao. Fora do escopo minimo deste milestone.

Consequencias
Contrato formal de broker existe ✅

PaperBroker conforme ao contrato ✅

MT5Adapter oferece assinatura simetrica ✅

Caminho para broker mockado em testes ✅

8 testes de conformidade protegem contra regressao ✅

Divida arquitetural P3.c permanece documentada

text

---