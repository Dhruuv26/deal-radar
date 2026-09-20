"""
P3: True Price & Deal Score Computation.

Implements REQ-P3-1 (rolling baseline from price history), REQ-P3-2
(flagging a discount as genuine or not), REQ-P3-3 (composite 0-100 deal
score), and REQ-P3-4 (recompute whenever new price or review data lands).
"""
import statistics
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models
from . import reviews as reviews_service

BASELINE_WINDOW_DAYS = 30          # REQ-P3-1
GENUINE_DISCOUNT_THRESHOLD = 0.05  # REQ-P3-2: within 5% of baseline = not a real drop

PRICE_SCORE_WEIGHT = 0.6           # REQ-P3-3: documented, adjustable weighting
REVIEW_SCORE_WEIGHT = 0.4


def compute_rolling_baseline(db: Session, listing_id: int, before: datetime = None) -> float:
    """REQ-P3-1: median listed_price over the last 30 days of history.

    Falls back to whatever history exists if there isn't a full 30 days
    yet — a brand-new listing's very first snapshot has no baseline to
    compare against other than itself.
    """
    before = before or datetime.utcnow()
    window_start = before - timedelta(days=BASELINE_WINDOW_DAYS)

    prices = [
        row.listed_price
        for row in db.query(models.PriceSnapshot)
        .filter(
            models.PriceSnapshot.listing_id == listing_id,
            models.PriceSnapshot.recorded_at >= window_start,
            models.PriceSnapshot.recorded_at < before,
        )
        .all()
    ]
    if not prices:
        return None
    return statistics.median(prices)


def evaluate_discount(current_price: float, baseline: float) -> tuple:
    """REQ-P3-2: decide whether the current price is a genuine drop.

    Returns (true_price, is_genuine_discount).
    """
    if baseline is None:
        # No history yet — nothing to compare against, so treat the listed
        # price as-is and leave the genuineness flag undetermined.
        return current_price, None

    if current_price >= baseline * (1 - GENUINE_DISCOUNT_THRESHOLD):
        # Within 5% of baseline (or higher) — not a genuine price drop.
        return baseline, False

    return current_price, True


def compute_price_score(true_price: float, baseline: float) -> float:
    """0-100: bigger genuine gap below baseline -> higher score."""
    if baseline is None or baseline == 0:
        return 50.0  # neutral — not enough history to judge yet
    discount_fraction = max(0.0, (baseline - true_price) / baseline)
    return min(100.0, discount_fraction * 400)  # a 25% genuine discount already maxes the score


def compute_and_store_deal_score(db: Session, listing: models.Listing) -> models.DealScore:
    """REQ-P3-3, REQ-P3-4: combine price and review scores into one
    composite deal score and persist it. Call this after both a new
    PriceSnapshot and updated ReviewSignal rows exist for the listing.
    """
    latest_snapshot = (
        db.query(models.PriceSnapshot)
        .filter(models.PriceSnapshot.listing_id == listing.listing_id)
        .order_by(models.PriceSnapshot.recorded_at.desc())
        .first()
    )
    baseline = compute_rolling_baseline(db, listing.listing_id, before=latest_snapshot.recorded_at)
    price_score = compute_price_score(latest_snapshot.true_price, baseline)
    review_score = reviews_service.compute_review_score(listing)
    composite = PRICE_SCORE_WEIGHT * price_score + REVIEW_SCORE_WEIGHT * review_score

    deal_score = models.DealScore(
        listing_id=listing.listing_id,
        price_score=round(price_score, 2),
        review_score=round(review_score, 2),
        composite_score=round(composite, 2),
        computed_at=datetime.utcnow(),
    )
    db.add(deal_score)
    db.flush()
    return deal_score
