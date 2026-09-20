"""
Orchestrates one full refresh cycle for a listing, tying together P2
(ingestion), P3 (pricing/deal score), P4 (review signals), and P5
(watchlist threshold checks) — mirroring the six-step pipeline in the
project's DFD (Level 2, P2 decomposition) and use case diagram
(Refresh Price Data -> its six <<include>> sub-steps).

Used by:
  - routers/ingestion.py's manual "refresh now" endpoint (for demos, since
    waiting for the real 6-hour schedule isn't practical to show)
  - services/scheduler.py's periodic APScheduler job (REQ-P2-1)
"""
import re
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models
from . import ingestion, pricing, reviews as reviews_service

logger = logging.getLogger("deal_radar.refresh")

ALERT_THROTTLE_HOURS = 24  # REQ-P5-3


def parse_offer_text(offer_text: str):
    """REQ-P2-3: turn free-text offer descriptions into a structured
    (offer_type, discount_value). Returns None if there's no active offer.
    """
    if not offer_text:
        return None

    percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", offer_text)
    discount_value = float(percent_match.group(1)) if percent_match else 0.0

    text_lower = offer_text.lower()
    if "bank" in text_lower or "card" in text_lower:
        offer_type = "bank_discount"
    elif "coupon" in text_lower:
        offer_type = "coupon"
    elif "emi" in text_lower:
        offer_type = "emi"
    else:
        offer_type = "other"

    return offer_type, discount_value


def refresh_listing(db: Session, listing: models.Listing) -> dict:
    """Runs the full pipeline for one listing and returns a small summary
    dict (used by the manual refresh endpoint and by tests)."""
    client = ingestion.get_retailer_client(listing.retailer.name)
    category_name = listing.product.category.name

    try:
        raw = client.fetch_listing(listing.product_url, listing.retailer_sku, category_name)
    except Exception as exc:
        # REQ-P2-4: a failed fetch (including robots.txt blocking or the
        # scraper's page structure no longer matching) marks this
        # listing's data as stale rather than crashing the whole refresh.
        logger.warning("Refresh failed for listing %s: %s", listing.listing_id, exc)
        return {
            "listing_id": listing.listing_id,
            "listed_price": None,
            "true_price": None,
            "is_genuine_discount": None,
            "composite_score": None,
            "alert_triggered": False,
            "error": str(exc),
        }

    # --- P2: persist the raw price observation (REQ-P2-2: append, never overwrite) ---
    baseline = pricing.compute_rolling_baseline(db, listing.listing_id, before=raw.fetched_at)
    true_price, is_genuine = pricing.evaluate_discount(raw.listed_price, baseline)

    snapshot = models.PriceSnapshot(
        listing_id=listing.listing_id,
        listed_price=raw.listed_price,
        true_price=true_price,
        is_genuine_discount=is_genuine,
        recorded_at=raw.fetched_at,
    )
    db.add(snapshot)

    # --- P2: parse and persist any offer (REQ-P2-3) ---
    parsed_offer = parse_offer_text(raw.offer_text)
    if parsed_offer:
        offer_type, discount_value = parsed_offer
        db.add(models.Offer(listing_id=listing.listing_id, offer_type=offer_type, discount_value=discount_value))

    db.flush()

    # --- P4: extract review signals from the fetched snippets ---
    reviews_service.extract_review_signals(db, listing, raw.review_snippets)

    # --- P3: compute and store the composite deal score ---
    deal_score = pricing.compute_and_store_deal_score(db, listing)

    # --- P5: check watchlist threshold, respecting the 24h throttle ---
    alert_triggered = check_watchlist_threshold(db, listing, deal_score)

    db.commit()

    return {
        "listing_id": listing.listing_id,
        "listed_price": raw.listed_price,
        "true_price": true_price,
        "is_genuine_discount": is_genuine,
        "composite_score": deal_score.composite_score,
        "alert_triggered": alert_triggered,
    }


def check_watchlist_threshold(db: Session, listing: models.Listing, deal_score: models.DealScore) -> bool:
    """REQ-P5-3: if this listing is watchlisted and its new score crosses
    the stored threshold, "trigger" an alert — throttled to at most one
    per 24 hours. Actual delivery (email/SMS) isn't wired up yet; see
    SRS Appendix C, TBD-2. This records that an alert *would* fire.
    """
    item = (
        db.query(models.WatchlistItem)
        .filter(models.WatchlistItem.listing_id == listing.listing_id)
        .first()
    )
    if item is None or deal_score.composite_score < item.threshold_score:
        return False

    now = datetime.utcnow()
    if item.last_alerted_at and now - item.last_alerted_at < timedelta(hours=ALERT_THROTTLE_HOURS):
        return False  # already alerted within the throttle window

    item.last_alerted_at = now
    db.add(item)
    return True


def refresh_all_listings(db: Session) -> list:
    """REQ-P2-1: refresh every tracked listing. Called by both the
    scheduled job and the manual refresh-now endpoint."""
    listings = db.query(models.Listing).all()
    return [refresh_listing(db, listing) for listing in listings]
