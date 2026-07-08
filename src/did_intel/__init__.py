"""
DIDRepChecker — Phone number reputation checking for VoIP professionals.

Core modules:
    - scraper: Async RoboKiller scraper engine
    - cache: SQLite cache with TTL expiration
    - api: FastAPI REST server
    - cli: Interactive command-line interface
    - config: Centralized configuration management
"""

__version__ = "2.0.0"
__all__ = ["scraper", "cache", "api", "cli", "config"]
