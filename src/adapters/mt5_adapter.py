import logging
from typing import Dict, Any, Optional

from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order, Signal
from src.risk.calculators import SLTPCalculator
from src.risk.config import RiskConfig

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    mt5 = None
    HAS_MT5 = False


class MT5Adapter:
    """
    Adaptador de integracao com o MetaTrader 5 para coleta de dados e
    execucao de ordens.

    Calcula stop_loss e take_profit via SLTPCalculator antes de enviar
    ordens ao MT5 (usa ATR se disponivel em signal.metadata, senao
    percentual fixo definido em RiskConfig).
    """

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        risk_config: Optional[RiskConfig] = None,
    ):
        self.login = login
        self.password = password
        self.server = server
        self.is_connected = False
        self.risk_config = risk_config or RiskConfig()
        self.sltp_calc = SLTPCalculator(self.risk_config)

    def initialize(self) -> bool:
        if not HAS_MT5:
            logger.warning(
                "MetaTrader5 nao esta instalado. Operando em modo desacoplado/mock."
            )
            self.is_connected = True
            return True

        init_kwargs = {}
        if self.login:
            init_kwargs["login"] = self.login
        if self.password:
            init_kwargs["password"] = self.password
        if self.server:
            init_kwargs["server"] = self.server

        if mt5.initialize(**init_kwargs):
            self.is_connected = True
            logger.info("Conexao com MetaTrader 5 estabelecida com sucesso.")
            return True
        else:
            logger.error(f"Falha ao conectar no MetaTrader 5: {mt5.last_error()}")
            self.is_connected = False
            return False

    def shutdown(self) -> None:
        if HAS_MT5 and self.is_connected:
            mt5.shutdown()
        self.is_connected = False
        logger.info("Conexao com MetaTrader 5 encerrada.")

    def get_account_info(self) -> Dict[str, Any]:
        if not self.is_connected:
            return {"balance": 0.0, "equity": 0.0, "margin": 0.0}

        if HAS_MT5 and mt5:
            info = mt5.account_info()
            if info is not None:
                return {
                    "login": info.login,
                    "balance": float(info.balance),
                    "equity": float(info.equity),
                    "margin": float(info.margin),
                    "free_margin": float(info.margin_free),
                    "leverage": info.leverage,
                }

        return {
            "balance": 100000.0,
            "equity": 100000.0,
            "margin": 0.0,
            "free_margin": 100000.0,
            "leverage": 100,
        }

    def fetch_latest_bar(self, symbol: str) -> Dict[str, Any]:
        if HAS_MT5 and self.is_connected and mt5:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
            if rates is not None and len(rates) > 0:
                bar = rates[0]
                return {
                    "symbol": symbol,
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "volume": float(bar["tick_volume"]),
                    "timestamp": int(bar["time"]),
                }

        return {
            "symbol": symbol,
            "open": 100.0,
            "high": 102.0,
            "low": 99.5,
            "close": 101.0,
            "volume": 1500.0,
            "timestamp": 1700000000,
        }

    def _compute_sltp(
        self, signal: Signal, entry_price: float
    ) -> tuple:
        """Calcula (stop_loss, take_profit) usando SLTPCalculator."""
        atr_val = None
        if isinstance(signal.metadata, dict):
            atr_val = signal.metadata.get("atr")

        try:
            stop_loss, take_profit = self.sltp_calc.calculate(
                direction=signal.direction,
                entry_price=entry_price,
                atr=atr_val,
            )
        except Exception as exc:
            logger.warning(
                "Falha ao calcular SL/TP (%s). Usando fallback default_sl_pct.", exc
            )
            sl_distance = entry_price * (self.risk_config.default_sl_pct / 100.0)
            tp_distance = sl_distance * self.risk_config.reward_to_risk_ratio
            if signal.direction == SignalDirection.BUY:
                stop_loss = entry_price - sl_distance
                take_profit = entry_price + tp_distance
            else:
                stop_loss = entry_price + sl_distance
                take_profit = entry_price - tp_distance

        return round(stop_loss, 4), round(take_profit, 4)

    def execute_signal(self, signal: Signal, bar: Dict[str, Any]) -> Order:
        """
        Converte um sinal em ordem e envia para execucao no MT5.
        Inclui stop_loss e take_profit calculados via SLTPCalculator.
        """
        price = float(bar.get("close", 100.0))
        stop_loss, take_profit = self._compute_sltp(signal, price)

        quantity = 1.0
        if isinstance(signal.metadata, dict):
            quantity = float(signal.metadata.get("quantity", 1.0))

        if not self.is_connected:
            return Order(
                symbol=signal.symbol,
                direction=signal.direction,
                quantity=quantity,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status=OrderStatus.REJECTED,
            )

        if HAS_MT5 and mt5:
            order_type = (
                mt5.ORDER_TYPE_BUY
                if signal.direction == SignalDirection.BUY
                else mt5.ORDER_TYPE_SELL
            )
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": quantity,
                "type": order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": 10,
                "magic": 100100,
                "comment": "DayTradeAI_AutoOrder",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            result = mt5.order_send(request)
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                return Order(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    quantity=quantity,
                    price=result.price if result.price > 0 else price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=OrderStatus.FILLED,
                )
            else:
                ret_code = result.retcode if result else "NO_RESULT"
                logger.error(f"Erro ao enviar ordem no MT5. Retcode: {ret_code}")
                return Order(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    quantity=quantity,
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status=OrderStatus.REJECTED,
                )

        # Simulacao (sem MT5 instalado)
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=quantity,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.FILLED,
        )