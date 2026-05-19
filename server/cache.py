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

        if db_path is not None:
            self.db_path = db_path
            logger.info(f"Using user-provided cache path: {self.db_path}")
            return

        # Use environment variable if set
        env_cache_dir = os.environ.get("REPUTATION_CACHE_DIR")
        if env_cache_dir:
            cache_dir = Path(env_cache_dir)
        else:
            # Determine OS-specific default
            if sys.platform == "win32":
                base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
                cache_dir = base_dir / "DIDRepChecker"
            else:
                # Linux/macOS production default
                cache_dir = Path("/var/cache/DIDRepChecker")

        # Ensure the directory exists and is writable
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Test write access
            test_file = cache_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            self.db_path = str(cache_dir / "reputation_cache.db")
            logger.info(f"Cache database path: {self.db_path}")
        except Exception as e:
            logger.warning(f"Cannot write to {cache_dir}: {e}. Falling back to in-memory cache.")
            self.db_path = ":memory:"
            logger.info("Using in-memory cache (no persistence across restarts).")

    async def _init_db(self):
        """Create the database and tables if they don't exist."""
        if self._initialized:
            return

        if self.db_path == ":memory:":
            async with aiosqlite.connect(self.db_path) as db:
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
            self._initialized = True
            return

        # File-based database
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
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
        self._initialized = True

    async def get_uncached(self, numbers: List[str]) -> Tuple[Dict[str, Dict[str, str]], List[str]]:
        if not numbers:
            return {}, []

        await self._init_db()
        current_time = time.time()
        cached_results = {}
        numbers_to_scrape = []

        try:
            async with aiosqlite.connect(self.db_path) as db:
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
            async with aiosqlite.connect(self.db_path) as db:
                await db.executemany('''
                    INSERT OR REPLACE INTO reputation 
                    (phone_number, reputation, robokiller_status, user_reports, total_calls, last_call, scraped_at, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', rows)
                await db.commit()
        except Exception as e:
            logger.error(f"Cache write error: {e}")

    async def cleanup_expired(self):
        await self._init_db()
        current_time = time.time()
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM reputation 
                    WHERE ? - timestamp > ?
                ''', (current_time, self.ttl_seconds))
                await db.commit()
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")