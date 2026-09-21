from datetime import datetime, timedelta
from typing import Dict, List
from src.domain.enums import Timeframe
from src.domain.models import Candle


class TimeSeriesResampler:
    TIMEFRAME_MINUTES: Dict[Timeframe, int] = {
        Timeframe.M1: 1,
        Timeframe.M5: 5,
        Timeframe.M15: 15,
        Timeframe.H1: 60,
        Timeframe.D1: 1440,
    }

    @classmethod
    def resample(cls, candles: List[Candle], target_tf: Timeframe) -> List[Candle]:
        if not candles:
            return []

        sorted_candles = sorted(candles, key=lambda c: c.timestamp)
        source_tf = sorted_candles[0].timeframe

        target_minutes = cls.TIMEFRAME_MINUTES[target_tf]
        source_minutes = cls.TIMEFRAME_MINUTES[source_tf]

        if target_minutes < source_minutes:
            raise ValueError(
                f"Impossível realizar downsampling de {source_tf.value} para {target_tf.value}"
            )

        if target_minutes == source_minutes:
            return sorted_candles

        resampled: List[Candle] = []
        current_group: List[Candle] = []
        current_bucket_start: datetime | None = None

        for candle in sorted_candles:
            bucket_start = cls._get_bucket_start(candle.timestamp, target_minutes)

            if current_bucket_start is None:
                current_bucket_start = bucket_start

            if bucket_start == current_bucket_start:
                current_group.append(candle)
            else:
                resampled.append(
                    cls._aggregate_group(current_group, target_tf, current_bucket_start)
                )
                current_group = [candle]
                current_bucket_start = bucket_start

        if current_group and current_bucket_start is not None:
            resampled.append(
                cls._aggregate_group(current_group, target_tf, current_bucket_start)
            )

        return resampled

    @staticmethod
    def _get_bucket_start(dt: datetime, minutes: int) -> datetime:
        minute_offset = dt.minute % minutes
        bucket_dt = dt.replace(second=0, microsecond=0) - timedelta(minutes=minute_offset)
        return bucket_dt

    @staticmethod
    def _aggregate_group(
        group: List[Candle], target_tf: Timeframe, bucket_start: datetime
    ) -> Candle:
        open_price = group[0].open
        close_price = group[-1].close
        high_price = max(c.high for c in group)
        low_price = min(c.low for c in group)
        total_volume = sum(c.volume for c in group)

        return Candle(
            symbol=group[0].symbol,
            timeframe=target_tf,
            timestamp=bucket_start,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
        )