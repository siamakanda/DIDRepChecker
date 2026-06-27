"""
FastAPI server for DID Intel
Provides a /scrape endpoint that returns reputation data for a list of phone numbers.
Supports optional API key authentication.
"""

from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import List, Dict
from contextlib import asynccontextmanager
import asyncio
import logging
import time
from did_intel.scraper import RoboKillerScraper
from did_intel.config import get_config, reload_config
from did_intel.metrics import metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("did_intel.api")

# ----------------------------------------------------------------------
# Scraper instance (reused across requests)
# ----------------------------------------------------------------------
scraper = RoboKillerScraper()

# ----------------------------------------------------------------------
# API Key authentication
# ----------------------------------------------------------------------
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    FastAPI dependency: validate the X-API-Key header.
    Skips check if api_key_required is False (backward compatible).
    Config is cached — use POST /admin/reload-config to pick up runtime changes.
    """
    cfg = get_config()

    if not cfg.get("api_key_required", False):
        return True  # Auth disabled — allow all

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header. Get an API key from the server admin.",
        )

    allowed = cfg.get("allowed_api_keys", [])
    if api_key not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

    return True


# ----------------------------------------------------------------------
# FastAPI app setup
# ----------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing scraper session and cache")
    await scraper.start()
    await scraper.cache._init_db()

    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            await scraper.cache.cleanup_expired()

    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("Startup complete — ready for requests")

    yield

    logger.info("Shutting down — cancelling cleanup and closing scraper")
    cleanup_task.cancel()
    await scraper.close()
    logger.info("Shutdown complete")

app = FastAPI(
    title="DID Reputation API",
    description="Returns reputation, total calls, user reports, and last call for phone numbers.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS — restricted to known clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",           # Chrome extensions
        "moz-extension://*",              # Firefox extensions
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# In-memory rate limiter (per-IP token bucket)
# ----------------------------------------------------------------------
_rate_buckets: dict = {}  # ip -> (tokens, last_refill)

RATE_LIMIT_RPS = 30       # requests per second per IP
RATE_LIMIT_BURST = 60     # max burst


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ("/health", "/metrics"):
        return await call_next(request)
    client = request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1")
    now = time.time()
    if client not in _rate_buckets:
        _rate_buckets[client] = (RATE_LIMIT_BURST, now)
    tokens, last = _rate_buckets[client]
    tokens = min(RATE_LIMIT_BURST, tokens + (now - last) * RATE_LIMIT_RPS)
    if tokens < 1:
        remaining = int((1 - tokens) / RATE_LIMIT_RPS * 1000)
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limited", "detail": f"Too many requests. Retry in {remaining}ms."},
            headers={"Retry-After": str(max(1, remaining // 1000))},
        )
    _rate_buckets[client] = (tokens - 1, now)
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    client = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    logger.info(f"{request.method} {request.url.path}  {response.status_code}  {elapsed_ms:.0f}ms  client={client}")
    metrics.inc("requests_total")
    metrics.add_duration("request_duration", (time.perf_counter() - start))
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": f"HTTP {exc.status_code}", "detail": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )

# ----------------------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------------------
class NumbersRequest(BaseModel):
    numbers: List[str] = Field(..., min_length=1, description="List of phone numbers")

class NumberResult(BaseModel):
    phone_number: str
    reputation: str
    robokiller_status: str
    user_reports: str
    total_calls: str
    last_call: str
    scraped_at: str


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""


# Maximum numbers allowed per scrape request (configurable)
MAX_NUMBERS_PER_REQUEST = 500

# ----------------------------------------------------------------------
# Endpoints
# ----------------------------------------------------------------------
@app.post("/scrape", response_model=List[NumberResult])
async def scrape_numbers(
    request: NumbersRequest,
    _auth: bool = Depends(verify_api_key),
):
    """
    Accept a list of phone numbers and return reputation data.

    Requires `X-API-Key` header when API key auth is enabled.
    """
    try:
        if len(request.numbers) > MAX_NUMBERS_PER_REQUEST:
            raise HTTPException(
                status_code=400,
                detail=f"Too many numbers. Maximum {MAX_NUMBERS_PER_REQUEST} per request, got {len(request.numbers)}.",
            )
        metrics.inc("scrape_requests")
        results = await scraper.scrape_async(request.numbers)
        metrics.inc("numbers_scraped", len(request.numbers))
        cache_hits = sum(1 for r in results if r.get("reputation") not in ("Error", "Blocked", "Timeout", "ConnectionError"))
        metrics.inc("cache_hits", cache_hits)
        return results
    except HTTPException:
        raise
    except Exception as e:
        metrics.inc("scrape_errors")
        logger.error(f"Scrape endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy"}


@app.post("/admin/reload-config", response_model=Dict[str, str])
async def admin_reload_config():
    """
    Hot-reload configuration from disk (e.g. after updating API keys).
    """
    reload_config()
    cfg = get_config()
    logger.info("Configuration reloaded via admin endpoint")
    return {
        "status": "ok",
        "api_key_required": str(cfg.get("api_key_required", False)),
        "allowed_keys_count": str(len(cfg.get("allowed_api_keys", []))),
    }


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus text-format metrics endpoint.
    """
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics.render(), media_type="text/plain")


def main():
    """Entry point for `didintel-server` console script."""
    import uvicorn
    from did_intel.config import get_config
    cfg = get_config()
    uvicorn.run(
        "did_intel.api:app",
        host=cfg.get("api_host", "0.0.0.0"),
        port=cfg.get("api_port", 8000),
        reload=cfg.get("api_reload", False),
    )


if __name__ == "__main__":
    main()