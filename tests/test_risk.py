from datetime import datetime, timezone
from src.domain.enums import SignalType, Timeframe
from src.domain.models import Signal
from src.risk.config import RiskConfig
from src.risk.engine import RiskEngine


def create_mock_signal(direction: SignalType, metadata: dict = None) -> Signal:
    return Signal(
        symbol="WIN",
        timeframe=Timeframe.M5,
        timestamp=datetime.now(timezone.utc),
        direction=direction,
        metadata=metadata or {}
    )


def test_risk_manager_drawdown_limit():
    engine = RiskEngine()
    engine.manager.update_state(daily_pnl_pct=-6.0, open_positions_count=0) # Máximo é -5.0
    
    signal = create_mock_signal(SignalType.BUY)
    order = engine.generate_order(signal, current_price=100.0, account_balance=10000.0)
    
    assert order is None  # Rejeitado por limite de drawdown diário


def test_risk_manager_max_positions_limit():
    config = RiskConfig(max_open_positions=2)
    engine = RiskEngine(config)
    engine.manager.update_state(daily_pnl_pct=1.0, open_positions_count=2)
    
    signal = create_mock_signal(SignalType.BUY)
    order = engine.generate_order(signal, current_price=100.0, account_balance=10000.0)
    
    assert order is None  # Rejeitado por bater limite de posições abertas


def test_position_sizer_math():
    engine = RiskEngine(RiskConfig(risk_per_trade_pct=1.0))
    # Saldo 10.000, risco 1% = R$ 100
    # Entrada 100, Stop 99 (1% default) = Risco por unidade R$ 1
    # Lote esperado = 100 / 1 = 100 unidades
    
    signal = create_mock_signal(SignalType.BUY)
    order = engine.generate_order(signal, current_price=100.0, account_balance=10000.0)
    
    assert order is not None
    assert order.quantity == 100.0
    assert order.stop_loss == 99.0  # SL padrão de 1%
    assert order.take_profit == 102.0 # TP RR de 2.0

def test_sltp_dynamic_atr():
    engine = RiskEngine()
    # Mock de sinal com ATR calculado no metadado
    signal = create_mock_signal(SignalType.SELL, metadata={"atr": 2.0})
    
    # ATR 2.0 -> SL_dist = 2 * 1.5 = 3.0
    # TP_dist = 3.0 * 2.0 (RR) = 6.0
    # Sell @ 100.0 -> SL = 103.0, TP = 94.0
    order = engine.generate_order(signal, current_price=100.0, account_balance=10000.0)
    
    assert order is not None
    assert order.stop_loss == 103.0
    assert order.take_profit == 94.0