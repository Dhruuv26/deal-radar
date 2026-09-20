"""
Pydantic schemas for request/response validation.

Covers P1 (catalog), P3 (price history / deal score), P4 (review signals),
and P5 (watchlist) — the full 70%-checkpoint surface. P6 (dashboard) has
no dedicated schemas yet since it's a frontend-only increment reading
from the endpoints these schemas already describe.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CategoryOut(BaseModel):
    category_id: int
    name: str

    class Config:
        from_attributes = True


class RetailerOut(BaseModel):
    retailer_id: int
    name: str
    has_api: bool

    class Config:
        from_attributes = True


class ListingCreate(BaseModel):
    retailer_id: int = Field(..., description="ID of an existing retailer")
    retailer_sku: str = Field(..., min_length=1, max_length=100)
    product_url: str = Field(..., min_length=1, max_length=500)


class ListingOut(BaseModel):
    listing_id: int
    retailer_id: int
    retailer_sku: str
    product_url: str
    retailer: RetailerOut

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    brand: Optional[str] = Field(None, max_length=100)
    category_id: int
    listing: ListingCreate


class ProductOut(BaseModel):
    product_id: int
    name: str
    brand: Optional[str]
    category: CategoryOut
    listings: List[ListingOut] = []

    class Config:
        from_attributes = True


class ProductSearchResult(BaseModel):
    product_id: int
    name: str
    brand: Optional[str]
    category_name: str
    listing_count: int


# ---------------------------------------------------------------------
# P3: True price / deal score
# ---------------------------------------------------------------------

class PriceSnapshotOut(BaseModel):
    snapshot_id: int
    listed_price: float
    true_price: Optional[float]
    is_genuine_discount: Optional[bool]
    recorded_at: datetime

    class Config:
        from_attributes = True


class DealScoreOut(BaseModel):
    score_id: int
    price_score: Optional[float]
    review_score: Optional[float]
    composite_score: Optional[float]
    computed_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# P4: Review signals
# ---------------------------------------------------------------------

class ReviewSignalOut(BaseModel):
    keyword_tag: str
    mention_count: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# P5: Watchlist
# ---------------------------------------------------------------------

class WatchlistCreate(BaseModel):
    listing_id: int
    threshold_score: float = Field(..., ge=0, le=100)


class WatchlistOut(BaseModel):
    watchlist_id: int
    listing_id: int
    threshold_score: float
    last_alerted_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------
# Ingestion (manual refresh trigger)
# ---------------------------------------------------------------------

class RefreshResult(BaseModel):
    listing_id: int
    listed_price: Optional[float]
    true_price: Optional[float]
    is_genuine_discount: Optional[bool]
    composite_score: Optional[float]
    alert_triggered: bool
    error: Optional[str] = None


class RefreshSummary(BaseModel):
    listings_refreshed: int
    alerts_triggered: int
    results: List[RefreshResult]
