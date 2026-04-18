"""
Modular, Reusable Scraper Engine for RoboKiller Lookup
Can be used as a library, from CLI, or from an API.
"""

import asyncio
import aiohttp
import random
import time
import re
import logging
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from lxml import html
from server.cache import ReputationCache

# ----------------------------------------------------------------------
# Configuration defaults
# ----------------------------------------------------------------------
DEFAULT_CONFIG = {
    "base_url": "https://lookup.robokiller.com",
    "concurrent_requests": 30,
    "timeout": 15,
    "connect_timeout": 5,
    "sock_read_timeout": 10,
    "max_retries": 2,
    "requests_per_second": 5,
    "connection_limit": 100,
    "keepalive_timeout": 30,
    "rotate_user_agents": True,
    "rotate_headers": True,
    "referer_chance": 0.5,
}

# User agents (shortened list – keep your full list)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

LANGUAGE_MAP = {
    "en-US,en;q=0.9": ["Chrome", "Firefox", "Edge"],
    "en-GB,en;q=0.9": ["Safari"],
}

REFERER_SOURCES = [
    "https://www.google.com/",
    "https://www.bing.com/",
    "",
]

# ----------------------------------------------------------------------
# Helper functions (stateless)
# ----------------------------------------------------------------------
def clean_number(number) -> str:
    """Extract 10-digit phone number from any input."""
    if not number or not isinstance(number, (str, int)):
        return ""
    cleaned = ''.join(filter(str.isdigit, str(number)))
    if cleaned.startswith('1') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned if len(cleaned) == 10 else ""


def get_random_headers() -> Dict[str, str]:
    """Generate random HTTP headers for anti‑detection."""
    user_agent = random.choice(USER_AGENTS)
    browser_type = "Chrome"
    if "Firefox" in user_agent:
        browser_type = "Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        browser_type = "Safari"
    compatible_languages = [lang for lang, browsers in LANGUAGE_MAP.items() if browser_type in browsers]
    accept_language = random.choice(compatible_languages) if compatible_languages else "en-US,en;q=0.9"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": user_agent,
        "DNT": random.choice(["0", "1"]),
        "Connection": "keep-alive",
    }
    if random.random() > DEFAULT_CONFIG["referer_chance"]:
        headers["Referer"] = random.choice(REFERER_SOURCES)
    return headers


def parse_robokiller_html(html_content: str, phone_number: str) -> Dict[str, str]:
    """Extract reputation, status, calls, reports from RoboKiller HTML."""
    try:
        tree = html.fromstring(html_content)
        data = {
            "phone_number": phone_number,
            "reputation": "Unknown",
            "robokiller_status": "Unknown",
            "user_reports": "0",
            "total_calls": "0",
            "last_call": "N/A",
            "scraped_at": datetime.now().isoformat()
        }
        if "not found" in html_content.lower() or "does not exist" in html_content.lower():
            data['reputation'] = "Not Found"
            data['robokiller_status'] = "N/A"
            return data

        found_reputation = False
        user_rep_div = tree.xpath('//div[@id="userReputation"]')
        if user_rep_div:
            found_reputation = True
            h3_texts = user_rep_div[0].xpath('.//h3/text()')
            if h3_texts:
                rep_text = h3_texts[0].strip()
                class_attr = user_rep_div[0].get('class', '')
                if 'green' in class_attr or 'Positive' in rep_text:
                    data['reputation'] = 'Positive'
                elif 'red' in class_attr or 'Negative' in rep_text:
                    data['reputation'] = 'Negative'
                elif 'yellow' in class_attr or 'Neutral' in rep_text:
                    data['reputation'] = 'Neutral'
                else:
                    data['reputation'] = rep_text

        robo_status_div = tree.xpath('//div[@id="roboStatus"]')
        if robo_status_div:
            found_reputation = True
            h3_texts = robo_status_div[0].xpath('.//h3/text()')
            if h3_texts:
                status_text = h3_texts[0].strip()
                class_attr = robo_status_div[0].get('class', '')
                if 'green' in class_attr or 'Allowed' in status_text:
                    data['robokiller_status'] = 'Allowed'
                elif 'red' in class_attr or 'Blocked' in status_text:
                    data['robokiller_status'] = 'Blocked'
                else:
                    data['robokiller_status'] = status_text

        reports_div = tree.xpath('//div[@id="userReports"]')
        if reports_div:
            h3_texts = reports_div[0].xpath('.//h3/text()')
            if h3_texts:
                numbers = re.findall(r'[\d,]+', h3_texts[0].strip())
                if numbers:
                    data['user_reports'] = numbers[0].replace(',', '')

        calls_div = tree.xpath('//div[@id="totalCall"]')
        if calls_div:
            h3_texts = calls_div[0].xpath('.//h3/text()')
            if h3_texts:
                numbers = re.findall(r'[\d,]+', h3_texts[0].strip())
                if numbers:
                    data['total_calls'] = numbers[0].replace(',', '')

        last_call_div = tree.xpath('//div[@id="lastCall"]')
        if last_call_div:
            h3_texts = last_call_div[0].xpath('.//h3/text()')
            if h3_texts:
                data['last_call'] = h3_texts[0].strip()

        if found_reputation:
            return data
        if len(html_content) > 5000:
            data['reputation'] = "No Data Available"
        else:
            data['reputation'] = "Invalid Page"
        return data
    except Exception as e:
        logging.error(f"Parse error for {phone_number}: {e}")
        return {
            "phone_number": phone_number,
            "reputation": "Parse Error",
            "robokiller_status": "",
            "user_reports": "0",
            "total_calls": "0",
            "last_call": "N/A",
            "scraped_at": datetime.now().isoformat(),
        }


# ----------------------------------------------------------------------
# Rate limiter (internal)
# ----------------------------------------------------------------------
class RateLimiter:
    def __init__(self, rate_per_second: float):
        self.rate = max(rate_per_second, 0.1)
        self.capacity = max(self.rate, 1.0)
        self.tokens = self.capacity
        self.updated_at = time.time()
        self.cooldown_until = 0.0
        self.failure_count = 0

    async def acquire(self):
        now = time.time()
        if now < self.cooldown_until:
            await asyncio.sleep(self.cooldown_until - now)
            now = time.time()
        elapsed = now - self.updated_at
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.updated_at = now
        if self.tokens < 1:
            sleep_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(sleep_time)
            self.tokens = self.capacity
            self.updated_at = time.time()
        self.tokens -= 1

    def record_429(self):
        backoff_seconds = min(10 * (2 ** self.failure_count), 120)
        self.cooldown_until = time.time() + backoff_seconds
        self.failure_count += 1

    def reset_failures(self):
        self.failure_count = max(0, self.failure_count - 1)


# ----------------------------------------------------------------------
# Main scraper class (API‑ready)
# ----------------------------------------------------------------------
class RoboKillerScraper:
    """Reusable scraper for RoboKiller phone number lookup."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        self.cache = ReputationCache()

    async def _fetch_one(self, session: aiohttp.ClientSession,
                         phone_number: str,
                         semaphore: asyncio.Semaphore,
                         rate_limiter: RateLimiter,
                         progress_callback: Optional[Callable] = None) -> Dict[str, str]:
        async with semaphore:
            await rate_limiter.acquire()
            formatted = f"{phone_number[:3]}-{phone_number[3:6]}-{phone_number[6:]}"
            url = f"{self.config['base_url']}/p/{formatted}"
            headers = get_random_headers()
            timeout = aiohttp.ClientTimeout(
                total=self.config["timeout"],
                connect=self.config["connect_timeout"],
                sock_read=self.config["sock_read_timeout"]
            )
            for attempt in range(self.config["max_retries"] + 1):
                try:
                    async with session.get(url, headers=headers, timeout=timeout) as resp:
                        if resp.status == 403:
                            result = self._error_result(phone_number, "Blocked")
                        elif resp.status == 429:
                            rate_limiter.record_429()
                            await asyncio.sleep(2 ** attempt)
                            continue
                        elif resp.status == 200:
                            html_content = await resp.text()
                            block_indicators = ["captcha", "access denied", "cloudflare", "blocked"]
                            if any(ind in html_content.lower() for ind in block_indicators):
                                result = self._error_result(phone_number, "Blocked")
                            else:
                                result = parse_robokiller_html(html_content, phone_number)
                        else:
                            result = self._error_result(phone_number, f"HTTP {resp.status}")
                except asyncio.TimeoutError:
                    result = self._error_result(phone_number, "Timeout")
                except aiohttp.ClientConnectorError:
                    result = self._error_result(phone_number, "ConnectionError")
                except Exception:
                    result = self._error_result(phone_number, "Error")
                else:
                    if progress_callback:
                        await progress_callback(phone_number, result)
                    return result

                if attempt < self.config["max_retries"]:
                    await asyncio.sleep(1 * (attempt + 1))

            result = self._error_result(phone_number, "Error")
            if progress_callback:
                await progress_callback(phone_number, result)
            return result

    def _error_result(self, phone_number: str, reason: str) -> Dict[str, str]:
        return {
            "phone_number": phone_number,
            "reputation": reason,
            "robokiller_status": "",
            "user_reports": "0",
            "total_calls": "0",
            "last_call": "N/A",
            "scraped_at": datetime.now().isoformat(),
        }

    async def scrape_async(self,
                           phone_numbers: List[str],
                           progress_callback: Optional[Callable] = None) -> List[Dict[str, str]]:
        """Asynchronous scrape – ideal for API endpoints."""
        if not phone_numbers:
            return []

        # 1. Check Cache
        cached_results, numbers_to_scrape = await self.cache.get_uncached(phone_numbers)
        
        # 2. Trigger progress callback for cached items
        if progress_callback:
            for num, res in cached_results.items():
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(num, res)
                else:
                    progress_callback(num, res)

        # 3. If everything was cached, return early
        if not numbers_to_scrape:
            return list(cached_results.values())

        connector = aiohttp.TCPConnector(
            limit=self.config["connection_limit"],
            keepalive_timeout=self.config["keepalive_timeout"],
            force_close=False,
        )
        rate_limiter = RateLimiter(self.config["requests_per_second"])
        semaphore = asyncio.Semaphore(self.config["concurrent_requests"])
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self._fetch_one(session, num, semaphore, rate_limiter, progress_callback)
                for num in numbers_to_scrape
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            valid_new_results = [r for r in results if not isinstance(r, Exception)]
            
            # 4. Save new results to cache
            await self.cache.save(valid_new_results)
            
            # 5. Return combined list
            return list(cached_results.values()) + valid_new_results

    def scrape(self,
               phone_numbers: List[str],
               progress_callback: Optional[Callable] = None) -> List[Dict[str, str]]:
        """Synchronous wrapper – convenient for CLI."""
        if progress_callback is not None and not asyncio.iscoroutinefunction(progress_callback):
            async def async_cb(num, res):
                progress_callback(num, res)
                return True
            cb = async_cb
        else:
            cb = progress_callback
        return asyncio.run(self.scrape_async(phone_numbers, cb))


# ----------------------------------------------------------------------
# Backward compatibility for existing CLI scripts
# ----------------------------------------------------------------------
_legacy_scraper = RoboKillerScraper()

def scrape_numbers_sync(phone_numbers: List[str],
                        progress_callback: Optional[Callable] = None) -> List[Dict[str, str]]:
    """Legacy synchronous wrapper (kept for compatibility)."""
    return _legacy_scraper.scrape(phone_numbers, progress_callback)

__all__ = ["RoboKillerScraper", "clean_number", "scrape_numbers_sync", "DEFAULT_CONFIG"]