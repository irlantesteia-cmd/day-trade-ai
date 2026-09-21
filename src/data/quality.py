from enum import Enum
from typing import List
from src.domain.models import Candle


class QualityStatus(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"
    STALE = "STALE"


class DataQualityReport:
    def __init__(self, status: QualityStatus, issues: List[str]) -> None:
        self.status = status
        self.issues = issues

    @property
    def is_valid(self) -> bool:
        return self.status in [QualityStatus.VALID, QualityStatus.WARNING]


class DataQualityEngine:
    @staticmethod
    def validate_candles(candles: List[Candle]) -> DataQualityReport:
        issues: List[str] = []

        if not candles:
            return DataQualityReport(
                QualityStatus.INVALID, ["O conjunto de candles está vazio."]
            )

        seen_timestamps = set()
        last_ts = None

        for candle in candles:
            # 1. Duplicidade
            if candle.timestamp in seen_timestamps:
                issues.append(f"Timestamp duplicado detectado: {candle.timestamp}")
            seen_timestamps.add(candle.timestamp)

            # 2. Ordenação temporal
            if last_ts is not None and candle.timestamp <= last_ts:
                issues.append(
                    f"Inconsistência temporal: candle {candle.timestamp} <= anterior {last_ts}"
                )

            # 3. Preço/Volume inválidos
            if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
                issues.append(f"Preço inválido (<= 0) no candle {candle.timestamp}")

            if candle.volume < 0:
                issues.append(f"Volume negativo no candle {candle.timestamp}")

            last_ts = candle.timestamp

        # Classificação do status
        if any("duplicado" in issue or "Inconsistência" in issue for issue in issues):
            return DataQualityReport(QualityStatus.INVALID, issues)
        elif issues:
            return DataQualityReport(QualityStatus.WARNING, issues)

        return DataQualityReport(QualityStatus.VALID, [])