"""
FastAPI server for DID Intel
Provides a /scrape endpoint that returns reputation data for a list of phone numbers.
Supports optional API key authentication.
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import List, Dict
from contextlib import asynccontextmanager
import asyncio
import logging
from did_intel.scraper import RoboKillerScraper
from did_intel.config import reload_config

logger = logging.getLogger(__name__)

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
    Config is re-read on every request so changes take effect without restart.
    """
    cfg = reload_config()

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
    # Startup
    await scraper.start()
    await scraper.cache._init_db()  # ensure cache db exists
    
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(3600)  # Every hour
            await scraper.cache.cleanup_expired()
            
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    await scraper.close()

app = FastAPI(
    title="DID Reputation API",
    description="Returns reputation, total calls, user reports, and last call for phone numbers.",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for Chrome extension and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        results = await scraper.scrape_async(request.numbers)
        return results
    except Exception as e:
        logger.error(f"Scrape endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy"}


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