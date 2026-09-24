"""
Features de volatilidade (nao-direcionais).

Diferente das features em price_action/technical, estas descrevem o
TAMANHO do movimento, nao a direcao. Usadas para testar se e possivel
prever "vai ter movimento grande" independente de subir/cair.

Hipotese cientifica: volatilidade tem memoria (volatility clustering,
Engle 1982). Se verdadeira, e previsivel.

Features:
  - RealizedVolatilityExtractor(period): std dos log returns em janela
  - VolatilityRatioExtractor(short, long): vol curta / vol longa
  - RangeRatioExtractor(period): (high - low)/close medio em janela
  - BollingerWidthExtractor(period): (upper - lower) / middle
"""
import math
from typing import Any, Dict, List, Optional

from src.domain.models import Candle
from src.features.base import FeatureExtractor


def _log_returns(closes: List[float]) -> List[float]:
    """Retorna log returns entre closes consecutivos."""
    returns = []
    for i in range(1, len(closes)):
        c0, c1 = closes[i - 1], closes[i]
        if c0 > 0 and c1 > 0:
            returns.append(math.log(c1 / c0))
        else:
            returns.append(0.0)
    return returns


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(var)


class RealizedVolatilityExtractor(FeatureExtractor):
    """Desvio padrao dos log returns nas ultimas N barras."""

    def __init__(self, period: int = 20) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"realized_vol_{self.period}"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        key = f"realized_vol_{self.period}"
        # Precisa de period+1 candles para gerar period log returns
        if len(candles) < self.period + 1:
            return {key: None}

        closes = [c.close for c in candles[-(self.period + 1):]]
        returns = _log_returns(closes)
        vol = _std(returns)
        return {key: round(vol, 8)}


class VolatilityRatioExtractor(FeatureExtractor):
    """
    Razao entre vol curta e vol longa.

    > 1: volatilidade crescendo (expansao)
    < 1: volatilidade caindo (contracao / squeeze)
    """

    def __init__(self, short_period: int = 5, long_period: int = 20) -> None:
        if short_period >= long_period:
            raise ValueError("short_period deve ser < long_period")
        self.short_period = short_period
        self.long_period = long_period

    @property
    def name(self) -> str:
        return f"vol_ratio_{self.short_period}_{self.long_period}"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        key = f"vol_ratio_{self.short_period}_{self.long_period}"
        if len(candles) < self.long_period + 1:
            return {key: None}

        closes = [c.close for c in candles[-(self.long_period + 1):]]
        returns = _log_returns(closes)

        if len(returns) < self.long_period:
            return {key: None}

        short_returns = returns[-self.short_period:]
        long_returns = returns

        vol_short = _std(short_returns)
        vol_long = _std(long_returns)

        if vol_long == 0:
            return {key: 1.0}

        return {key: round(vol_short / vol_long, 6)}


class RangeRatioExtractor(FeatureExtractor):
    """Media de (high - low) / close nas ultimas N barras."""

    def __init__(self, period: int = 14) -> None:
        self.period = period

    @property
    def name(self) -> str:
        return f"range_ratio_{self.period}"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        key = f"range_ratio_{self.period}"
        if len(candles) < self.period:
            return {key: None}

        window = candles[-self.period:]
        ratios = []
        for c in window:
            if c.close > 0:
                ratios.append((c.high - c.low) / c.close)
        if not ratios:
            return {key: None}

        return {key: round(sum(ratios) / len(ratios), 8)}


class BollingerWidthExtractor(FeatureExtractor):
    """
    Largura das Bandas de Bollinger normalizada: (upper - lower) / middle.

    Squeeze (largura baixa) tende a preceder expansao.
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0) -> None:
        self.period = period
        self.std_dev = std_dev

    @property
    def name(self) -> str:
        return f"bb_width_{self.period}"

    def extract(
        self,
        candles: List[Candle],
        indicator_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[float]]:
        key = f"bb_width_{self.period}"
        if len(candles) < self.period:
            return {key: None}

        closes = [c.close for c in candles[-self.period:]]
        middle = sum(closes) / self.period
        if middle <= 0:
            return {key: None}

        std = _std(closes)
        width = (2 * self.std_dev * std) / middle
        return {key: round(width, 8)}