import time
import os
import logging
from typing import List, Dict, Tuple, Optional
import aiosqlite

class ReputationCache:
    """Async SQLite cache for RoboKiller reputation results."""

    def __init__(self, db_path: str = None, ttl_seconds: int = 86400):
        if db_path is None:
            self.db_path = os.path.join(os.path.dirname(__file__), "reputation_cache.db")
        else:
            self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._initialized = False

    async def _init_db(self):
        """Initialize the database and create tables if they don't exist."""
        if self._initialized:
            return

        # Ensure the directory exists if db_path is not just a filename
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

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
        """
        Check the cache for a list of numbers.
        Returns a tuple:
        - Dict of cached results {phone_number: result_dict}
        - List of numbers that are missing or expired (need to be scraped)
        """
        if not numbers:
            return {}, []

        await self._init_db()
        current_time = time.time()
        cached_results = {}
        numbers_to_scrape = []

        try:
            async with aiosqlite.connect(self.db_path) as db:
                # SQLite max variables is usually 999, so chunk the query if numbers list is huge
                chunk_size = 900
                for i in range(0, len(numbers), chunk_size):
                    chunk = numbers[i:i + chunk_size]
                    placeholders = ','.join('?' * len(chunk))
                    
                    async with db.execute(f"SELECT * FROM reputation WHERE phone_number IN ({placeholders})", chunk) as cursor:
                        async for row in cursor:
                            # row: (phone_number, reputation, status, user_reports, total_calls, last_call, scraped_at, timestamp)
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

            # Identify which numbers are missing or expired
            for num in numbers:
                if num not in cached_results:
                    numbers_to_scrape.append(num)
                    
        except Exception as e:
            logging.error(f"Cache read error: {e}")
            # If cache fails, degrade gracefully and scrape everything
            return {}, numbers

        return cached_results, numbers_to_scrape

    async def save(self, results: List[Dict[str, str]]):
        """Save new results to the cache."""
        if not results:
            return

        await self._init_db()
        current_time = time.time()

        # Prepare data for insertion
        rows = []
        for res in results:
            # Skip saving Parse Errors or generic Errors if we want to retry them later, 
            # but usually it's fine to cache a "Not Found" so we don't spam RoboKiller.
            # However, we'll cache everything and let TTL expire it.
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
            logging.error(f"Cache write error: {e}")
