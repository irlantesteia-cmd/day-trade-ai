"""
Adapter multi-ativo/multi-timeframe. Busca barras de N símbolos em M timeframes
e mantém um cache em memória por (symbol, timeframe).
"""
import time
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    mt5 = None


# Mapeamento nome → constante MT5
TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1  if HAS_MT5 else 1,
    "M5":  mt5.TIMEFRAME_M5  if HAS_MT5 else 5,
    "M15": mt5.TIMEFRAME_M15 if HAS_MT5 else 15,
    "M30": mt5.TIMEFRAME_M30 if HAS_MT5 else 30,
    "H1":  mt5.TIMEFRAME_H1  if HAS_MT5 else 60,
}


class MultiMarketAdapter:
    """
    Busca barras de vários símbolos e timeframes. Mantém cache para evitar
    chamadas repetidas ao MT5.
    """

    def __init__(self, symbols: List[str], timeframes: List[str] = None):
        self.symbols = symbols
        self.timeframes = timeframes or ["M1"]
        self._cache: Dict[Tuple[str, str], dict] = {}
        self.is_connected = False

    def initialize(self) -> bool:
        if not HAS_MT5:
            logger.warning("MT5 nao instalado. Operando em modo mock.")
            self.is_connected = True
            return True
        if not mt5.initialize():
            logger.error("Falha ao inicializar MT5: %s", mt5.last_error())
            return False
        self.is_connected = True
        # Adiciona todos os símbolos ao Market Watch
        for sym in self.symbols:
            info = mt5.symbol_info(sym)
            if info and not info.visible:
                mt5.symbol_select(sym, True)
        logger.info("MultiMarketAdapter conectado: %d symbols, %d timeframes",
                    len(self.symbols), len(self.timeframes))
        return True

    def fetch_bars(self, symbol: str, timeframe: str, n: int = 100) -> List[dict]:
        """
        Retorna as últimas N barras de (symbol, timeframe).
        Usa cache com TTL de 5s para evitar flood no MT5.
        """
        key = (symbol, timeframe)
        cached = self._cache.get(key)
        now = time.time()
        if cached and (now - cached["ts"]) < 5.0:
            return cached["bars"]

        if not (HAS_MT5 and self.is_connected):
            return []

        tf_const = TIMEFRAME_MAP.get(timeframe)
        if tf_const is None:
            logger.error("Timeframe desconhecido: %s", timeframe)
            return []

        rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, n)
        if rates is None or len(rates) == 0:
            logger.warning("Sem barras para %s %s: %s", symbol, timeframe, mt5.last_error())
            return []

        bars = [
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": float(r["tick_volume"]),
                "timestamp": int(r["time"]),
            }
            for r in rates
        ]
        self._cache[key] = {"ts": now, "bars": bars}
        return bars

    def fetch_all_latest(self) -> Dict[Tuple[str, str], dict]:
        """Retorna a última barra de cada (symbol, timeframe)."""
        out = {}
        for sym in self.symbols:
            for tf in self.timeframes:
                bars = self.fetch_bars(sym, tf, n=1)
                if bars:
                    out[(sym, tf)] = bars[-1]
        return out

    def shutdown(self):
        if HAS_MT5 and self.is_connected:
            mt5.shutdown()
        self.is_connected = False