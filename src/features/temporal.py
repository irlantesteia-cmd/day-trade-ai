import math
from typing import Any, Dict, List, Optional
from src.domain.models import Candle
from src.features.base import FeatureExtractor


class TimeOfDayExtractor(FeatureExtractor):
    @property
    def name(self) -> str:
        return "time_of_day"

    def extract(
        self, candles: List[Candle], indicator_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Optional[float]]:
        if not candles:
            return {"sin_time": None, "cos_time": None}

        ts = candles[-1].timestamp
        minute_of_day = ts.hour * 60 + ts.minute
        total_minutes_in_day = 1440.0

        # Codificação cíclica seno/cosseno para continuidade do horário
        radians = (minute_of_day / total_minutes_in_day) * 2.0 * math.pi
        return {
            "sin_time": round(math.sin(radians), 6),
            "cos_time": round(math.cos(radians), 6),
        }