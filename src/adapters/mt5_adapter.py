import logging
from typing import Dict, Any, Optional, List
from src.domain.enums import OrderStatus, SignalDirection
from src.domain.models import Order, Signal

logger = logging.getLogger(__name__)

# Tenta importar MetaTrader5; se não instalado/disponível, opera com suporte desacoplado
try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    mt5 = None
    HAS_MT5 = False


class MT5Adapter:
    """
    Adaptador de integracao com o MetaTrader 5 para coleta de dados e execucao de ordens.
    """

    def __init__(self, login: Optional[int] = None, password: Optional[str] = None, server: Optional[str] = None):
        self.login = login
        self.password = password
        self.server = server
        self.is_connected = False

    def initialize(self) -> bool:
        """Inicializa a conexao com o terminal MetaTrader 5."""
        if not HAS_MT5:
            logger.warning("MetaTrader5 nao esta instalado no ambiente Python. Operando em modo desacoplado/mock.")
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
        """Encerra a conexao com o MetaTrader 5."""
        if HAS_MT5 and self.is_connected:
            mt5.shutdown()
        self.is_connected = False
        logger.info("Conexao com MetaTrader 5 encerrada.")

    def get_account_info(self) -> Dict[str, Any]:
        """Obtem informacoes da conta (saldo, patrimonio, margem)."""
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

        # Fallback para ambiente sem terminal MT5 ativo
        return {"balance": 100000.0, "equity": 100000.0, "margin": 0.0, "free_margin": 100000.0, "leverage": 100}

    def fetch_latest_bar(self, symbol: str) -> Dict[str, Any]:
        """Obtem a barra mais recente do ativo configurado."""
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

        # Retorno sintético para testes / fallback
        return {
            "symbol": symbol,
            "open": 100.0,
            "high": 102.0,
            "low": 99.5,
            "close": 101.0,
            "volume": 1500.0,
            "timestamp": 1700000000,
        }

    def execute_signal(self, signal: Signal, bar: Dict[str, Any]) -> Order:
        """Converte um sinal em ordem e envia para execucao no MT5."""
        price = bar.get("close", 100.0)
        
        if not self.is_connected:
            return Order(
                symbol=signal.symbol,
                direction=signal.direction,
                quantity=1.0,
                price=price,
                status=OrderStatus.REJECTED,
            )

        if HAS_MT5 and mt5:
            order_type = mt5.ORDER_TYPE_BUY if signal.direction == SignalDirection.BUY else mt5.ORDER_TYPE_SELL
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": 1.0,
                "type": order_type,
                "price": price,
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
                    quantity=1.0,
                    price=result.price if result.price > 0 else price,
                    status=OrderStatus.FILLED,
                )
            else:
                ret_code = result.retcode if result else "NO_RESULT"
                logger.error(f"Erro ao enviar ordem no MT5. Retcode: {ret_code}")
                return Order(
                    symbol=signal.symbol,
                    direction=signal.direction,
                    quantity=1.0,
                    price=price,
                    status=OrderStatus.REJECTED,
                )

        # Simulação para ambiente sem terminal MT5
        return Order(
            symbol=signal.symbol,
            direction=signal.direction,
            quantity=1.0,
            price=price,
            status=OrderStatus.FILLED,
        )