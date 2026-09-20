"""
P2: Retailer Data Ingestion.

STATUS (70% checkpoint): the ingestion *pipeline* is fully wired end to end
(see services/refresh.py) — it's the retailer *data source* that's still
mocked. Per the SRS (Appendix C, TBD-1), Amazon PA-API access depends on
affiliate approval that is still pending, so RetailerAPIClient is backed by
MockRetailerClient here rather than a real HTTP client.

When Amazon PA-API / Flipkart Affiliate API access is confirmed, a real
subclass of RetailerAPIClient goes here and gets swapped in via
get_retailer_client() — nothing in P1, P3, P4, or P5 needs to change,
since they all depend only on the RawListingData shape below.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List
import random


@dataclass
class RawReviewSnippet:
    text: str
    verified_purchase: bool


@dataclass
class RawListingData:
    """What a retailer client returns for one listing — mirrors the raw
    inputs P2 parses into PriceSnapshot, Offer, and (via P4) ReviewSignal rows."""
    retailer_sku: str
    listed_price: float
    offer_text: str
    review_snippets: List[RawReviewSnippet]
    fetched_at: datetime


class RetailerAPIClient(ABC):
    """Interface every retailer data source implements."""

    @abstractmethod
    def fetch_listing(self, product_url: str, retailer_sku: str, category_name: str) -> RawListingData:
        raise NotImplementedError


# Review snippet pools, one per category, each tagged with whether it reads
# as a verified-purchase-style review. Mixed positive/negative so review
# signal extraction (P4) has something real to weight and count.
_REVIEW_POOL = {
    "keyboard": [
        ("Solid build quality, keys feel great after a month", True),
        ("Keycap wobble on the spacebar is annoying", True),
        ("Backlight is uneven across some keys", False),
        ("Switches feel mushy compared to my old board", True),
        ("Great typing experience, no complaints", True),
    ],
    "mouse": [
        ("Sensor lag when I move it too fast", True),
        ("Scroll wheel click is very satisfying", True),
        ("Grip feels comfortable for long sessions", False),
        ("Side buttons stopped responding after two weeks", True),
    ],
    "monitor": [
        ("Noticeable backlight bleed in dark scenes", True),
        ("Color accuracy is excellent out of the box", True),
        ("Some ghosting during fast motion in games", True),
        ("Stand wobbles a bit but panel quality is great", False),
    ],
    "webcam": [
        ("Autofocus keeps hunting in low light", True),
        ("Video quality is sharp in daylight", True),
        ("Mic picks up a lot of background noise", False),
    ],
    "headset": [
        ("Mic clarity is excellent for calls", True),
        ("Ear cups get uncomfortable after 2 hours", True),
        ("Bass is a bit boomy but overall good sound", False),
    ],
    "printer": [
        ("Paper jam issues within the first week", True),
        ("Print quality is crisp for the price", True),
        ("Ink smudges on glossy paper", False),
    ],
    "storage": [
        ("Read speeds match the advertised spec", True),
        ("Connector feels loose in some USB ports", True),
        ("Reliable so far after three months of use", False),
    ],
}

_OFFERS = [
    "10% instant discount with HDFC Bank cards",
    "No cost EMI available",
    "Extra 5% off with coupon SAVE5",
    "",  # no active offer
]


class MockRetailerClient(RetailerAPIClient):
    """
    Stand-in for the Amazon PA-API / Flipkart Affiliate API client.

    Returns plausible, randomized sample data (price, offer text, and a
    handful of category-appropriate review snippets) so the rest of the
    pipeline — true-price computation, review signal extraction, deal
    scoring, watchlist checks — can be built, tested, and demoed without
    live credentials. This is intentionally NOT connected to any real
    network call — see module docstring above.
    """

    def fetch_listing(self, product_url: str, retailer_sku: str, category_name: str) -> RawListingData:
        pool = _REVIEW_POOL.get(category_name, [])
        sample_size = min(3, len(pool)) if pool else 0
        chosen = random.sample(pool, sample_size) if sample_size else []
        snippets = [RawReviewSnippet(text=t, verified_purchase=v) for t, v in chosen]

        return RawListingData(
            retailer_sku=retailer_sku,
            listed_price=round(random.uniform(999, 8999), 2),
            offer_text=random.choice(_OFFERS),
            review_snippets=snippets,
            fetched_at=datetime.utcnow(),
        )


def get_retailer_client(retailer_name: str = None) -> RetailerAPIClient:
    """
    Factory used by the ingestion pipeline (services/refresh.py).

    "MD Computers" gets the real scraper (services/scraper_mdcomputers.py)
    — Amazon and Flipkart still get the mock client, since their official
    APIs turned out to be unreachable for a new project as of 2026 (see
    docs/Deal_Radar_SRS.docx, Appendix C, TBD-1). Swapping in a real
    Amazon/Flipkart client later just means adding a branch here — nothing
    downstream (P3, P4, P5) needs to change.
    """
    if retailer_name == "MD Computers":
        from .scraper_mdcomputers import MDComputersScraperClient
        return MDComputersScraperClient()
    return MockRetailerClient()
