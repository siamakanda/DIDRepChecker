import time
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import aiosqlite

logger = logging.getLogger(__name__)

class ReputationCache:
    """Async SQLite cache for RoboKiller reputation results."""

    def __init__(self, db_path: str = None, ttl_seconds: int = 86400):
        self.ttl_seconds = ttl_seconds
        self._initialized = False
        self._memory_conn: Optional[aiosqlite.Connection] = None

        if db_path is not None:
            self.db_path = db_path
            logger.info(f"Using user-provided cache path: {self.db_path}")
            return

        if sys.platform == "win32":
            base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            cache_dir = base_dir / "DIDRepChecker"
        else:
            cache_dir = Path.home() / ".cache" / "DIDRepChecker"

        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            test_file = cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            self.db_path = str(cache_dir / "reputation_cache.db")
            logger.info(f"Cache database path: {self.db_path}")
        except Exception as e:
            logger.warning(f"Cannot write to {cache_dir}: {e}. Falling back to in-memory cache.")
            self.db_path = ":memory:"
            logger.info("Using in-memory cache (no persistence across restarts).")

    async def _get_db(self) -> aiosqlite.Connection:
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = await aiosqlite.connect(":memory:")
            return self._memory_conn
        return await aiosqlite.connect(self.db_path)

    async def _init_db(self):
        if self._initialized:
            return

        db = await self._get_db()
        try:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS reputation (
                    phone_number TEXT PRIMARY KEY,
                    reputation TEXT,
                    robokiller_status TEXT,
                    user_reports TEXT,
                    total_calls TEXT,
                    last_call TEXT,
                    scraped_at TEXT,
                    timestamp REAL
                )
            ''')
            await db.commit()
        finally:
            if self.db_path != ":memory:":
                await db.close()

        self._initialized = True

    async def get_uncached(self, numbers: List[str]) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
        if not numbers:
            return {}, []

        await self._init_db()
        current_time = time.time()
        cached_results = {}
        numbers_to_scrape = []

        try:
            db = await self._get_db()
            try:
                chunk_size = 900
                for i in range(0, len(numbers), chunk_size):
                    chunk = numbers[i:i + chunk_size]
                    placeholders = ','.join('?' * len(chunk))
                    async with db.execute(f"SELECT * FROM reputation WHERE phone_number IN ({placeholders})", chunk) as cursor:
                        async for row in cursor:
                            phone_number = row[0]
                            timestamp = row[7]
                            if current_time - timestamp <= self.ttl_seconds:
                                cached_results[phone_number] = {
                                    "phone_number": phone_number,
                                    "reputation": row[1],
                                    "robokiller_status": row[2],
                                    "user_reports": row[3],
                                    "total_calls": row[4],
                                    "last_call": row[5],
                                    "scraped_at": row[6]
                                }
            finally:
                if self.db_path != ":memory:":
                    await db.close()

            for num in numbers:
                if num not in cached_results:
                    numbers_to_scrape.append(num)
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return {}, numbers

        return cached_results, numbers_to_scrape

    async def save(self, results: List[Dict[str, str]]):
        if not results:
            return

        await self._init_db()
        current_time = time.time()
        rows = []
        for res in results:
            rows.append((
                res.get("phone_number"),
                res.get("reputation", "Unknown"),
                res.get("robokiller_status", ""),
                res.get("user_reports", "0"),
                res.get("total_calls", "0"),
                res.get("last_call", "N/A"),
                res.get("scraped_at", ""),
                current_time
            ))

        try:
            db = await self._get_db()
            try:
                await db.executemany('''
                    INSERT OR REPLACE INTO reputation 
                    (phone_number, reputation, robokiller_status, user_reports, total_calls, last_call, scraped_at, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', rows)
                await db.commit()
            finally:
                if self.db_path != ":memory:":
                    await db.close()
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    async def cleanup_expired(self):
        await self._init_db()
        current_time = time.time()
        try:
            db = await self._get_db()
            try:
                await db.execute('''
                    DELETE FROM reputation 
                    WHERE ? - timestamp > ?
                ''', (current_time, self.ttl_seconds))
                await db.execute('''
                    DELETE FROM reputation
                    WHERE rowid NOT IN (
                        SELECT rowid FROM reputation
                        ORDER BY timestamp DESC
                        LIMIT 50000
                    )
                ''')
                await db.commit()
            finally:
                if self.db_path != ":memory:":
                    await db.close()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")

    async def close(self):
        if self._memory_conn is not None:
            await self._memory_conn.close()
            self._memory_conn = None
            self._initialized = False
