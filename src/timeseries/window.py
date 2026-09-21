from typing import Generator, List
from src.domain.models import Candle


class RollingWindowEngine:
    @staticmethod
    def get_windows(
        candles: List[Candle], window_size: int
    ) -> Generator[List[Candle], None, None]:
        """
        Retorna janelas滑动 (rolling windows) estritamente contendo dados até o instante t.
        Previne Look-Ahead Bias garantindo que dados futuros t+1 nunca integrem a janela atual.
        """
        if window_size <= 0:
            raise ValueError("O tamanho da janela deve ser maior que zero.")

        n = len(candles)
        if n < window_size:
            return

        for i in range(window_size, n + 1):
            yield candles[i - window_size : i]