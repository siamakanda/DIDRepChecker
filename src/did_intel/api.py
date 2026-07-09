"""
FastAPI server for DIDRepChecker
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("did_intel.api")

scraper = RoboKillerScraper()
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    cfg = get_config()
    if not cfg.get("api_key_required", False):
        return True
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if api_key not in cfg.get("allowed_api_keys", []):
        raise HTTPException(status_code=403, detail="Invalid API key.")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DIDRepChecker API server")
    await scraper.start()
    await scraper.cache._init_db()

    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)
            await scraper.cache.cleanup_expired()

    cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    logger.info("Shutting down DIDRepChecker API server")
    cleanup_task.cancel()
    await scraper.close()


app = FastAPI(
    title="DIDRepChecker API",
    description="Bulk phone number reputation lookup via RoboKiller.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "moz-extension://*",
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_buckets: dict = {}
RATE_LIMIT_RPS = 30
RATE_LIMIT_BURST = 60


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/health":
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
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})


class NumbersRequest(BaseModel):
    numbers: List[str] = Field(..., min_length=1)


class NumberResult(BaseModel):
    phone_number: str
    reputation: str
    robokiller_status: str
    user_reports: str
    total_calls: str
    last_call: str
    scraped_at: str


MAX_NUMBERS_PER_REQUEST = 500


@app.post("/scrape", response_model=List[NumberResult])
async def scrape_numbers(request: NumbersRequest, _auth: bool = Depends(verify_api_key)):
    try:
        if len(request.numbers) > MAX_NUMBERS_PER_REQUEST:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_NUMBERS_PER_REQUEST} numbers per request.")
        return await scraper.scrape_async(request.numbers)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Scrape endpoint error")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/admin/reload-config")
async def admin_reload_config():
    reload_config()
    cfg = get_config()
    logger.info("Configuration reloaded")
    return {
        "status": "ok",
        "api_key_required": str(cfg.get("api_key_required", False)),
        "allowed_keys_count": str(len(cfg.get("allowed_api_keys", []))),
    }


def main():
    import uvicorn
    from did_intel.config import get_config
    cfg = get_config()
    logger.info("DIDRepChecker API starting on %s:%s", cfg.get("api_host", "0.0.0.0"), cfg.get("api_port", 8000))
    uvicorn.run("did_intel.api:app", host=cfg.get("api_host", "0.0.0.0"), port=cfg.get("api_port", 8000), log_level="info", access_log=False)


if __name__ == "__main__":
    main()
