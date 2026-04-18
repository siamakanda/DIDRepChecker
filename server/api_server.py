"""
FastAPI server for DID Reputation Checker
Provides a /scrape endpoint that returns reputation data for a list of phone numbers.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict
from server.scraper_engine import RoboKillerScraper

# ----------------------------------------------------------------------
# FastAPI app setup
# ----------------------------------------------------------------------
app = FastAPI(
    title="DID Reputation API",
    description="Returns reputation, total calls, user reports, and last call for phone numbers.",
    version="2.0.0"
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
# Scraper instance (reused across requests)
# ----------------------------------------------------------------------
scraper = RoboKillerScraper()

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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "healthy"}