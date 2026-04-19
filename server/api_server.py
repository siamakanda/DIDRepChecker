"""
FastAPI server for DID Reputation Checker
Provides a /scrape endpoint that returns reputation data for a list of phone numbers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict
from contextlib import asynccontextmanager
import asyncio
import logging
from server.scraper_engine import RoboKillerScraper

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Scraper instance (reused across requests)
# ----------------------------------------------------------------------
scraper = RoboKillerScraper()

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
async def scrape_numbers(request: NumbersRequest):
    """
    Accept a list of phone numbers and return reputation data.
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