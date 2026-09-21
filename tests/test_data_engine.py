from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.data.database import Base
from src.data.providers.mock_provider import MockMarketDataProvider
from src.data.quality import DataQualityEngine, QualityStatus
from src.data.repository import CandleRepository
from src.domain.enums import Timeframe
from src.domain.models import Candle


def test_mock_provider_fetches_candles():
    provider = MockMarketDataProvider()
    start = datetime.now(timezone.utc)
    end = start + timedelta(minutes=5)
    candles = provider.fetch_candles("WIN", Timeframe.M1, start, end)

    assert len(candles) > 0
    assert candles[0].symbol == "WIN"


def test_data_quality_engine_valid():
    start = datetime.now(timezone.utc)
    c1 = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=start,
        open=10.0,
        high=11.0,
        low=9.5,
        close=10.5,
        volume=100.0,
    )
    c2 = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=start + timedelta(minutes=1),
        open=10.5,
        high=12.0,
        low=10.0,
        close=11.5,
        volume=120.0,
    )

    report = DataQualityEngine.validate_candles([c1, c2])
    assert report.status == QualityStatus.VALID
    assert report.is_valid is True


def test_data_quality_engine_detects_out_of_order():
    start = datetime.now(timezone.utc)
    c1 = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=start + timedelta(minutes=1),
        open=10.0,
        high=11.0,
        low=9.5,
        close=10.5,
        volume=100.0,
    )
    c2 = Candle(
        symbol="WIN",
        timeframe=Timeframe.M1,
        timestamp=start,  # Timestamp anterior (fora de ordem)
        open=10.5,
        high=12.0,
        low=10.0,
        close=11.5,
        volume=120.0,
    )

    report = DataQualityEngine.validate_candles([c1, c2])
    assert report.status == QualityStatus.INVALID
    assert report.is_valid is False


def test_candle_repository_persistence():
    # Banco SQLite em memória para o teste unitário
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    repo = CandleRepository(session)
    start = datetime.now(timezone.utc)

    candles = [
        Candle(
            symbol="WIN",
            timeframe=Timeframe.M1,
            timestamp=start,
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=500.0,
        )
    ]

    saved_count = repo.save_candles(candles)
    assert saved_count == 1

    fetched = repo.get_candles("WIN", Timeframe.M1)
    assert len(fetched) == 1
    assert fetched[0].close == 101.0
    session.close()