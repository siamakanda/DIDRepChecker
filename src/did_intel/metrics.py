"""
In-memory Prometheus metrics for DID Intel.
No external dependencies — plain text exposition format.
"""

import time
from collections import defaultdict
from typing import Dict


class Metrics:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._started_at = time.time()

    def inc(self, name: str, amount: int = 1):
        self._counters[name] += amount

    def add_duration(self, name: str, seconds: float):
        key_sum = name + "_sum"
        key_count = name + "_count"
        self._counters[key_sum] = self._counters.get(key_sum, 0.0) + seconds
        self._counters[key_count] += 1

    def render(self) -> str:
        lines = []
        lines.append(f"# HELP didintel_uptime_seconds Server uptime")
        lines.append(f"# TYPE didintel_uptime_seconds gauge")
        lines.append(f"didintel_uptime_seconds {time.time() - self._started_at:.3f}")

        duration_histograms = set()
        for k in self._counters:
            if k.endswith("_sum"):
                duration_histograms.add(k[:-4])
            elif k.endswith("_count") and k[:-6] in {h for h in duration_histograms if True}:
                pass

        lines.append(f"# HELP didintel_requests_total Total HTTP requests")
        lines.append(f"# TYPE didintel_requests_total counter")
        lines.append(f"didintel_requests_total {self._counters.get('requests_total', 0)}")

        lines.append(f"# HELP didintel_scrape_requests_total Scrape endpoint requests")
        lines.append(f"# TYPE didintel_scrape_requests_total counter")
        lines.append(f"didintel_scrape_requests_total {self._counters.get('scrape_requests', 0)}")

        lines.append(f"# HELP didintel_scrape_numbers_total Phone numbers scraped")
        lines.append(f"# TYPE didintel_scrape_numbers_total counter")
        lines.append(f"didintel_scrape_numbers_total {self._counters.get('numbers_scraped', 0)}")

        lines.append(f"# HELP didintel_cache_hits_total Cache hits")
        lines.append(f"# TYPE didintel_cache_hits_total counter")
        lines.append(f"didintel_cache_hits_total {self._counters.get('cache_hits', 0)}")

        lines.append(f"# HELP didintel_errors_total Scrape errors")
        lines.append(f"# TYPE didintel_errors_total counter")
        lines.append(f"didintel_errors_total {self._counters.get('scrape_errors', 0)}")

        # Request duration
        req_sum = self._counters.get("request_duration_sum", 0.0)
        req_count = self._counters.get("request_duration_count", 0)
        lines.append(f"# HELP didintel_request_duration_seconds HTTP request duration")
        lines.append(f"# TYPE didintel_request_duration_seconds summary")
        lines.append(f"didintel_request_duration_seconds_sum {req_sum:.6f}")
        lines.append(f"didintel_request_duration_seconds_count {req_count}")

        return "\n".join(lines) + "\n"


metrics = Metrics()
