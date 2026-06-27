import asyncio
import pytest
from did_intel.cache import ReputationCache


@pytest.fixture
def temp_cache(tmp_path):
    """Cache that uses a temp SQLite file."""
    db_path = tmp_path / "test_reputation.db"
    cache = ReputationCache(db_path=str(db_path), ttl_seconds=3600)
    return cache


@pytest.mark.asyncio
async def test_init_db(temp_cache):
    await temp_cache._init_db()
    # Verify table exists by inserting and reading
    result = {"phone_number": "2125551234", "reputation": "Positive",
              "robokiller_status": "Allowed", "user_reports": "0",
              "total_calls": "0", "last_call": "N/A", "scraped_at": "2024-01-01T00:00:00"}
    await temp_cache.save([result])
    cached, uncached = await temp_cache.get_uncached(["2125551234"])
    assert "2125551234" in cached
    assert len(uncached) == 0


@pytest.mark.asyncio
async def test_cache_hit(temp_cache):
    await temp_cache._init_db()
    result = {"phone_number": "2125551234", "reputation": "Positive",
              "robokiller_status": "Allowed", "user_reports": "0",
              "total_calls": "0", "last_call": "N/A", "scraped_at": "2024-01-01T00:00:00"}
    await temp_cache.save([result])

    cached, uncached = await temp_cache.get_uncached(["2125551234"])
    assert cached["2125551234"]["reputation"] == "Positive"
    assert uncached == []


@pytest.mark.asyncio
async def test_cache_miss(temp_cache):
    await temp_cache._init_db()
    cached, uncached = await temp_cache.get_uncached(["2125550000"])
    assert len(cached) == 0
    assert uncached == ["2125550000"]


@pytest.mark.asyncio
async def test_cache_partial(temp_cache):
    await temp_cache._init_db()
    result = {"phone_number": "2125551234", "reputation": "Positive",
              "robokiller_status": "Allowed", "user_reports": "0",
              "total_calls": "0", "last_call": "N/A", "scraped_at": "2024-01-01T00:00:00"}
    await temp_cache.save([result])

    cached, uncached = await temp_cache.get_uncached(["2125551234", "2125550000"])
    assert len(cached) == 1
    assert uncached == ["2125550000"]


@pytest.mark.asyncio
async def test_cache_overwrite(temp_cache):
    await temp_cache._init_db()
    r1 = {"phone_number": "2125551234", "reputation": "Negative",
          "robokiller_status": "Blocked", "user_reports": "5",
          "total_calls": "10", "last_call": "N/A", "scraped_at": "2024-01-01T00:00:00"}
    await temp_cache.save([r1])

    r2 = {"phone_number": "2125551234", "reputation": "Positive",
          "robokiller_status": "Allowed", "user_reports": "0",
          "total_calls": "0", "last_call": "N/A", "scraped_at": "2024-06-01T00:00:00"}
    await temp_cache.save([r2])

    cached, uncached = await temp_cache.get_uncached(["2125551234"])
    assert cached["2125551234"]["reputation"] == "Positive"


@pytest.mark.asyncio
async def test_empty_input(temp_cache):
    await temp_cache._init_db()
    cached, uncached = await temp_cache.get_uncached([])
    assert cached == {}
    assert uncached == []
