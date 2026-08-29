"""
Pydantic schemas for request/response validation.

Only covers the P1 (Product Search & Catalog Management) surface for this
30%-milestone increment. Schemas for price history, deal scores, review
signals, and watchlists will be added alongside their respective features.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


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
