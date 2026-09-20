"""
ORM models mirroring the Deal Radar Entity-Relationship Diagram
(see /docs/deal_radar_erd.mdj).

Implementation status (70% checkpoint — see README for full breakdown):
  - Category, Product, Retailer, Listing  -> P1
  - PriceSnapshot, Offer                  -> P2 (ingestion) + P3 (true price)
  - ReviewSignal                          -> P4 (review signal analysis)
  - DealScore                             -> P3 (deal scoring)
  - WatchlistItem                         -> P5 (watchlist, alert delivery still pending — SRS TBD-2)
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Float, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(100), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)

    category = relationship("Category", back_populates="products")
    listings = relationship("Listing", back_populates="product")


class Retailer(Base):
    __tablename__ = "retailers"

    retailer_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    has_api = Column(Boolean, default=False)

    listings = relationship("Listing", back_populates="retailer")


class Listing(Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("retailer_id", "retailer_sku", name="uq_retailer_sku"),
    )

    listing_id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    retailer_id = Column(Integer, ForeignKey("retailers.retailer_id"), nullable=False)
    retailer_sku = Column(String(100), nullable=False)
    product_url = Column(String(500), nullable=False)

    product = relationship("Product", back_populates="listings")
    retailer = relationship("Retailer", back_populates="listings")
    price_snapshots = relationship("PriceSnapshot", back_populates="listing")
    offers = relationship("Offer", back_populates="listing")
    review_signals = relationship("ReviewSignal", back_populates="listing")
    deal_scores = relationship("DealScore", back_populates="listing")


class PriceSnapshot(Base):
    """Populated by the P2 ingestion pipeline; true_price and
    is_genuine_discount are filled in by P3 (see services/pricing.py)."""
    __tablename__ = "price_snapshots"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    listed_price = Column(Float, nullable=False)
    true_price = Column(Float, nullable=True)
    is_genuine_discount = Column(Boolean, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="price_snapshots")


class Offer(Base):
    """Populated by the P2 ingestion pipeline (offer-text parsing)."""
    __tablename__ = "offers"

    offer_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    offer_type = Column(String(50), nullable=False)
    discount_value = Column(Float, nullable=False)

    listing = relationship("Listing", back_populates="offers")


class ReviewSignal(Base):
    """Populated by P4 (see services/reviews.py). Only aggregated keyword
    counts are stored — never verbatim review text (REQ-P4-3)."""
    __tablename__ = "review_signals"

    signal_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    keyword_tag = Column(String(100), nullable=False)
    mention_count = Column(Integer, default=0)

    listing = relationship("Listing", back_populates="review_signals")


class DealScore(Base):
    """Populated by P3 (see services/pricing.py)."""
    __tablename__ = "deal_scores"

    score_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    price_score = Column(Float, nullable=True)
    review_score = Column(Float, nullable=True)
    composite_score = Column(Float, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="deal_scores")


class WatchlistItem(Base):
    """P5: a listing the user wants to monitor, with an alert threshold."""
    __tablename__ = "watchlist_items"

    watchlist_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False, unique=True)
    threshold_score = Column(Float, nullable=False)
    last_alerted_at = Column(DateTime, nullable=True)  # enforces REQ-P5-3 (max 1 alert/24h)

    listing = relationship("Listing")
