"""
ORM models mirroring the Deal Radar Entity-Relationship Diagram
(see /docs/deal_radar_erd.mdj).

Implementation status (see README for full breakdown):
  - Category, Product, Retailer, Listing  -> fully used by P1 (this increment)
  - PriceSnapshot, Offer                  -> table defined, not yet populated (P2/P3, future increment)
  - ReviewSignal                          -> table defined, not yet populated (P4, future increment)
  - DealScore                             -> table defined, not yet populated (P3, future increment)

The later tables are included now so the schema in code matches the ERD
from day one, even though nothing writes to them yet.
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
    """Not yet populated — see P2/P3 in README's 'Not yet implemented' section."""
    __tablename__ = "price_snapshots"

    snapshot_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    listed_price = Column(Float, nullable=False)
    true_price = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="price_snapshots")


class Offer(Base):
    """Not yet populated — see P2 in README's 'Not yet implemented' section."""
    __tablename__ = "offers"

    offer_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    offer_type = Column(String(50), nullable=False)
    discount_value = Column(Float, nullable=False)

    listing = relationship("Listing", back_populates="offers")


class ReviewSignal(Base):
    """Not yet populated — see P4 in README's 'Not yet implemented' section."""
    __tablename__ = "review_signals"

    signal_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    keyword_tag = Column(String(100), nullable=False)
    mention_count = Column(Integer, default=0)

    listing = relationship("Listing", back_populates="review_signals")


class DealScore(Base):
    """Not yet populated — see P3 in README's 'Not yet implemented' section."""
    __tablename__ = "deal_scores"

    score_id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    price_score = Column(Float, nullable=True)
    review_score = Column(Float, nullable=True)
    composite_score = Column(Float, nullable=True)
    computed_at = Column(DateTime, default=datetime.utcnow)

    listing = relationship("Listing", back_populates="deal_scores")
