"""
P2: Retailer Data Ingestion — scaffolding only for this milestone.

STATUS (30% checkpoint): NOT wired to real retailer APIs yet.

Per the SRS (Appendix C, TBD-1), Amazon PA-API access depends on affiliate
approval that is still pending. Rather than block P1 (Product Search &
Catalog Management) on that external dependency, this module defines the
interface P2 will implement against, backed by a mock client that returns
realistic sample data. This lets P3 (deal scoring) and the frontend be
developed against a stable contract before live API credentials exist.

When Amazon PA-API / Flipkart Affiliate API access is confirmed, a real
subclass of RetailerAPIClient goes here and gets swapped in — nothing in
P1 or the API layer needs to change.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import random


@dataclass
class RawListingData:
    """What a retailer client returns for one listing — mirrors the raw
    inputs P2.1/P2.2 would parse into PriceSnapshot and Offer rows."""
    retailer_sku: str
    listed_price: float
    offer_text: str
    fetched_at: datetime


class RetailerAPIClient(ABC):
    """Interface every retailer data source implements (P2.1)."""

    @abstractmethod
    def fetch_listing(self, product_url: str, retailer_sku: str) -> RawListingData:
        raise NotImplementedError


class MockRetailerClient(RetailerAPIClient):
    """
    Stand-in for the Amazon PA-API / Flipkart Affiliate API client.

    Returns plausible-looking, randomized sample data so the rest of the
    pipeline (and the frontend) can be built and demoed without live
    credentials. This is intentionally NOT connected to any real network
    call — see class docstring above.
    """

    SAMPLE_OFFERS = [
        "10% instant discount with HDFC Bank cards",
        "No cost EMI available",
        "Extra 5% off with coupon SAVE5",
        "",  # no active offer
    ]

    def fetch_listing(self, product_url: str, retailer_sku: str) -> RawListingData:
        return RawListingData(
            retailer_sku=retailer_sku,
            listed_price=round(random.uniform(999, 8999), 2),
            offer_text=random.choice(self.SAMPLE_OFFERS),
            fetched_at=datetime.utcnow(),
        )


def get_retailer_client() -> RetailerAPIClient:
    """
    Factory used by the (future) scheduled ingestion job.

    Currently always returns the mock client. Once affiliate API access is
    confirmed, this becomes a lookup that picks the real client per
    retailer instead.
    """
    return MockRetailerClient()
