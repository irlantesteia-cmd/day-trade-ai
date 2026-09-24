"""
Cointegracao e pares trading.

Implementa:
  - Engle-Granger two-step test (regressao OLS + ADF sobre residuos)
  - Calculo de hedge ratio (beta)
  - Construcao de spread normalizado (z-score)
  - Half-life de reversao (via AR(1) sobre o spread)

Uso tipico:
    from src.portfolio.cointegration import CointegrationTester

    tester = CointegrationTester()
    result = tester.test(prices_a, prices_b)
    if result["is_cointegrated"]:
        spread = tester.build_spread(prices_a, prices_b, result["hedge_ratio"])
        z = tester.zscore(spread, window=20)
        # z > 2 -> abrir short no par; z < -2 -> abrir long
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CointegrationResult:
    """Resultado do teste de cointegracao entre dois ativos."""

    symbol_a: str
    symbol_b: str
    n_obs: int
    hedge_ratio: float
    intercept: float
    adf_stat: float
    adf_pvalue: float
    is_cointegrated: bool  # pvalue < threshold
    half_life: Optional[float] = None
    residual_std: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_a": self.symbol_a,
            "symbol_b": self.symbol_b,
            "n_obs": self.n_obs,
            "hedge_ratio": round(self.hedge_ratio, 6),
            "intercept": round(self.intercept, 6),
            "adf_stat": round(self.adf_stat, 4),
            "adf_pvalue": round(self.adf_pvalue, 6),
            "is_cointegrated": self.is_cointegrated,
            "half_life": round(self.half_life, 2) if self.half_life is not None else None,
            "residual_std": round(self.residual_std, 6),
            "notes": self.notes,
        }


class CointegrationTester:
    """
    Teste de cointegracao Engle-Granger e utilitarios de spread.

    Requer `statsmodels` (extra [stats] do pyproject).
    """

    # Limite pratico: half-life acima disso = "sem reversao util"
    MAX_HALF_LIFE_BARS = 1000

    def __init__(self, adf_pvalue_threshold: float = 0.05):
        if not 0 < adf_pvalue_threshold < 1:
            raise ValueError("adf_pvalue_threshold deve estar em (0, 1)")
        self.adf_pvalue_threshold = adf_pvalue_threshold

    # ------------------------------------------------------------------
    # Teste Engle-Granger
    # ------------------------------------------------------------------

    def test(
        self,
        prices_a: List[float],
        prices_b: List[float],
        symbol_a: str = "A",
        symbol_b: str = "B",
    ) -> CointegrationResult:
        """
        Executa Engle-Granger two-step:
          1. Regride prices_a ~ prices_b + intercept
          2. Testa ADF nos residuos

        H0: residuos possuem raiz unitaria (nao estacionarios)
        Se p-value < threshold: rejeita H0 -> cointegrados
        """
        if len(prices_a) != len(prices_b):
            raise ValueError(
                f"Series devem ter mesmo tamanho: {len(prices_a)} != {len(prices_b)}"
            )
        if len(prices_a) < 30:
            raise ValueError(f"Minimo 30 observacoes, recebido {len(prices_a)}")

        import statsmodels.api as sm
        from statsmodels.tsa.stattools import adfuller

        a = np.asarray(prices_a, dtype=float)
        b = np.asarray(prices_b, dtype=float)

        # Rejeita valores <= 0 (log inutil)
        if np.any(a <= 0) or np.any(b <= 0):
            return CointegrationResult(
                symbol_a=symbol_a, symbol_b=symbol_b,
                n_obs=len(a), hedge_ratio=0.0, intercept=0.0,
                adf_stat=0.0, adf_pvalue=1.0, is_cointegrated=False,
                notes="Precos nao-positivos detectados",
            )

        # Passo 1: OLS
        X = sm.add_constant(b)
        try:
            model = sm.OLS(a, X).fit()
        except Exception as exc:
            logger.exception("Falha no OLS")
            return CointegrationResult(
                symbol_a=symbol_a, symbol_b=symbol_b,
                n_obs=len(a), hedge_ratio=0.0, intercept=0.0,
                adf_stat=0.0, adf_pvalue=1.0, is_cointegrated=False,
                notes=f"OLS falhou: {exc}",
            )

        intercept = float(model.params[0])
        hedge_ratio = float(model.params[1])
        residuals = a - (intercept + hedge_ratio * b)

        # Passo 2: ADF (result_object=False silencia FutureWarning do statsmodels 0.15)
        try:
            adf_result = adfuller(residuals, autolag="AIC", result_object=False)
            adf_stat = float(adf_result[0])
            adf_pvalue = float(adf_result[1])
        except Exception as exc:
            logger.exception("Falha no ADF")
            return CointegrationResult(
                symbol_a=symbol_a, symbol_b=symbol_b,
                n_obs=len(a), hedge_ratio=hedge_ratio, intercept=intercept,
                adf_stat=0.0, adf_pvalue=1.0, is_cointegrated=False,
                notes=f"ADF falhou: {exc}",
            )

        is_coint = adf_pvalue < self.adf_pvalue_threshold
        half_life = self._estimate_half_life(residuals)
        residual_std = float(np.std(residuals))

        return CointegrationResult(
            symbol_a=symbol_a,
            symbol_b=symbol_b,
            n_obs=len(a),
            hedge_ratio=hedge_ratio,
            intercept=intercept,
            adf_stat=adf_stat,
            adf_pvalue=adf_pvalue,
            is_cointegrated=is_coint,
            half_life=half_life,
            residual_std=residual_std,
            notes="Engle-Granger",
        )

    # ------------------------------------------------------------------
    # Half-life de reversao (via AR(1) sobre os residuos)
    # ------------------------------------------------------------------

    def _estimate_half_life(self, residuals: np.ndarray) -> Optional[float]:
        """
        Estima half-life via AR(1): delta_y = alpha + beta * y_{t-1} + eps.
        Half-life = -ln(2) / ln(1 + beta).

        Retorna None se:
          - beta >= 0 (nao reverte / random walk)
          - half-life calculado excede MAX_HALF_LIFE_BARS (reversao
            lenta demais para ser util em trading intraday)
          - std dos residuos e proximo de zero (caso degenerado)
        """
        import statsmodels.api as sm

        y = np.asarray(residuals, dtype=float)
        y_lag = y[:-1]
        dy = np.diff(y)

        if len(dy) < 10:
            return None

        # Filtra valores patologicamente proximos de zero
        std_y = float(np.std(y_lag))
        if std_y < 1e-9:
            return None

        X = sm.add_constant(y_lag)
        try:
            model = sm.OLS(dy, X).fit()
            beta = float(model.params[1])
        except Exception:
            return None

        if beta >= 0:
            return None  # nao reverte

        one_plus_beta = 1.0 + beta
        if one_plus_beta <= 0:
            return None  # beta <= -1: formula invalida
        denom = np.log(one_plus_beta)
        if denom >= 0:
            return None

        hl = float(-np.log(2) / denom)
        if not np.isfinite(hl) or hl > self.MAX_HALF_LIFE_BARS:
            return None  # reversao muito lenta ou invalida
        return hl

    # ------------------------------------------------------------------
    # Construcao de spread
    # ------------------------------------------------------------------

    def build_spread(
        self,
        prices_a: List[float],
        prices_b: List[float],
        hedge_ratio: float,
        intercept: float = 0.0,
    ) -> List[float]:
        """Spread = A - (intercept + hedge_ratio * B)."""
        if len(prices_a) != len(prices_b):
            raise ValueError("Series devem ter mesmo tamanho")
        return [
            float(a - (intercept + hedge_ratio * b))
            for a, b in zip(prices_a, prices_b)
        ]

    def zscore(
        self,
        spread: List[float],
        window: int = 20,
    ) -> List[Optional[float]]:
        """
        Z-score do spread com media e desvio em janela movel.

        Retorna lista do mesmo tamanho; primeiros `window-1` sao None.
        """
        if window < 2:
            raise ValueError("window deve ser >= 2")
        if len(spread) < window:
            return [None] * len(spread)

        result: List[Optional[float]] = [None] * (window - 1)
        arr = np.asarray(spread, dtype=float)

        for i in range(window - 1, len(arr)):
            win = arr[i - window + 1 : i + 1]
            m = float(np.mean(win))
            s = float(np.std(win, ddof=1))
            if s == 0:
                result.append(0.0)
            else:
                result.append(float((arr[i] - m) / s))
        return result


# ---------------------------------------------------------------------------
# Wrapper para multiplos pares
# ---------------------------------------------------------------------------

def screen_pairs(
    prices_by_symbol: Dict[str, List[float]],
    min_correlation: float = 0.7,
    adf_pvalue_threshold: float = 0.05,
    min_obs: int = 100,
) -> List[CointegrationResult]:
    """
    Testa todos os pares (i, j) de um dict {symbol: prices} e retorna os
    que passam no threshold de cointegracao.

    Pre-filtra por correlacao de log-returns para evitar testar pares
    obviamente nao relacionados (reduz custo computacional).
    """
    import itertools

    tester = CointegrationTester(adf_pvalue_threshold=adf_pvalue_threshold)
    symbols = list(prices_by_symbol.keys())
    results: List[CointegrationResult] = []

    # Pre-computa log returns para filtro
    log_returns: Dict[str, np.ndarray] = {}
    for s, prices in prices_by_symbol.items():
        arr = np.asarray(prices, dtype=float)
        if len(arr) < min_obs:
            continue
        if np.any(arr <= 0):
            continue
        log_returns[s] = np.diff(np.log(arr))

    valid_symbols = list(log_returns.keys())

    for s1, s2 in itertools.combinations(valid_symbols, 2):
        r1 = log_returns[s1]
        r2 = log_returns[s2]
        n = min(len(r1), len(r2))
        if n < 30:
            continue

        corr = float(np.corrcoef(r1[-n:], r2[-n:])[0, 1])
        if abs(corr) < min_correlation:
            continue

        p1 = prices_by_symbol[s1]
        p2 = prices_by_symbol[s2]
        n_common = min(len(p1), len(p2))

        try:
            result = tester.test(
                p1[-n_common:], p2[-n_common:],
                symbol_a=s1, symbol_b=s2,
            )
        except Exception as exc:
            logger.debug("Falha testando %s/%s: %s", s1, s2, exc)
            continue

        if result.is_cointegrated:
            result.notes = f"corr={corr:.3f} | {result.notes}"
            results.append(result)

    # Ordena por p-value crescente
    results.sort(key=lambda r: r.adf_pvalue)
    return results