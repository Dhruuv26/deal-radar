"""
Tests for the P2->P3->P4->P5 refresh pipeline. Each test is tied to the
SRS requirement it verifies, matching the style of test_products.py.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app import models
from app.services import ingestion, pricing, reviews, refresh

engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def keyboard_listing(db):
    category = models.Category(name="keyboard")
    retailer = models.Retailer(name="Amazon.in", has_api=True)
    db.add_all([category, retailer])
    db.flush()

    product = models.Product(name="Test Keyboard", brand="TestBrand", category_id=category.category_id)
    db.add(product)
    db.flush()

    listing = models.Listing(
        product_id=product.product_id,
        retailer_id=retailer.retailer_id,
        retailer_sku="TEST-KB-1",
        product_url="https://example.com/kb1",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------------
# P2: offer text parsing (REQ-P2-3)
# ---------------------------------------------------------------------

def test_parse_offer_text_bank_discount():
    result = refresh.parse_offer_text("10% instant discount with HDFC Bank cards")
    assert result == ("bank_discount", 10.0)


def test_parse_offer_text_handles_decimal_percentage():
    """Regression test: real MD Computers data has decimal percentages
    like '7.5%', which an integer-only regex would misparse as '5.0'."""
    result = refresh.parse_offer_text("7.5% Instant Discount with HDFC Credit Card EMI")
    assert result == ("bank_discount", 7.5)


def test_parse_offer_text_coupon():
    result = refresh.parse_offer_text("Extra 5% off with coupon SAVE5")
    assert result == ("coupon", 5.0)


def test_parse_offer_text_none_when_empty():
    assert refresh.parse_offer_text("") is None


# ---------------------------------------------------------------------
# P3: true price / discount genuineness (REQ-P3-1, REQ-P3-2)
# ---------------------------------------------------------------------

def test_no_baseline_when_no_history(db, keyboard_listing):
    baseline = pricing.compute_rolling_baseline(db, keyboard_listing.listing_id)
    assert baseline is None


def test_evaluate_discount_flags_fake_discount_within_5_percent():
    true_price, is_genuine = pricing.evaluate_discount(current_price=970, baseline=1000)
    assert is_genuine is False
    assert true_price == 1000  # REQ-P3-2: not genuine -> true_price is the baseline


def test_evaluate_discount_flags_genuine_discount_beyond_5_percent():
    true_price, is_genuine = pricing.evaluate_discount(current_price=850, baseline=1000)
    assert is_genuine is True
    assert true_price == 850


def test_rolling_baseline_uses_median_of_last_30_days(db, keyboard_listing):
    now = datetime.utcnow()
    prices = [1000, 1000, 1200]  # median = 1000
    for i, price in enumerate(prices):
        db.add(models.PriceSnapshot(
            listing_id=keyboard_listing.listing_id,
            listed_price=price,
            recorded_at=now - timedelta(days=10 - i),
        ))
    db.commit()

    baseline = pricing.compute_rolling_baseline(db, keyboard_listing.listing_id, before=now)
    assert baseline == 1000


def test_rolling_baseline_ignores_snapshots_older_than_30_days(db, keyboard_listing):
    now = datetime.utcnow()
    db.add(models.PriceSnapshot(
        listing_id=keyboard_listing.listing_id, listed_price=5000, recorded_at=now - timedelta(days=45)
    ))
    db.add(models.PriceSnapshot(
        listing_id=keyboard_listing.listing_id, listed_price=1000, recorded_at=now - timedelta(days=5)
    ))
    db.commit()

    baseline = pricing.compute_rolling_baseline(db, keyboard_listing.listing_id, before=now)
    assert baseline == 1000  # the 45-day-old 5000 snapshot must be excluded


# ---------------------------------------------------------------------
# P4: review signal extraction (REQ-P4-1, REQ-P4-2, REQ-P4-3)
# ---------------------------------------------------------------------

def test_review_signals_use_category_specific_dictionary(db, keyboard_listing):
    snippets = [
        ingestion.RawReviewSnippet(text="Keycap wobble on the spacebar", verified_purchase=True),
        ingestion.RawReviewSnippet(text="Solid build quality overall", verified_purchase=False),
    ]
    signals = reviews.extract_review_signals(db, keyboard_listing, snippets)
    tags = {s.keyword_tag for s in signals}
    assert "keycap wobble" in tags
    assert "solid build" in tags


def test_verified_purchase_reviews_weighted_more_than_unverified(db, keyboard_listing):
    verified = [ingestion.RawReviewSnippet(text="keycap wobble is bad", verified_purchase=True)]
    unverified = [ingestion.RawReviewSnippet(text="keycap wobble is bad", verified_purchase=False)]

    verified_signals = reviews.extract_review_signals(db, keyboard_listing, verified)
    verified_count = next(s.mention_count for s in verified_signals if s.keyword_tag == "keycap wobble")

    unverified_signals = reviews.extract_review_signals(db, keyboard_listing, unverified)
    unverified_count = next(s.mention_count for s in unverified_signals if s.keyword_tag == "keycap wobble")

    assert verified_count > unverified_count


def test_no_verbatim_review_text_is_ever_stored(db, keyboard_listing):
    """REQ-P4-3."""
    snippets = [ingestion.RawReviewSnippet(text="Keycap wobble on the spacebar", verified_purchase=True)]
    reviews.extract_review_signals(db, keyboard_listing, snippets)

    # The model itself has no text column, so this is really a schema
    # guarantee — this test documents and locks that guarantee in.
    assert not hasattr(models.ReviewSignal, "review_text")
    assert not hasattr(models.ReviewSignal, "text")


# ---------------------------------------------------------------------
# P2->P5: full pipeline integration
# ---------------------------------------------------------------------

def test_refresh_listing_persists_snapshot_and_computes_score(db, keyboard_listing):
    result = refresh.refresh_listing(db, keyboard_listing)

    assert result["listing_id"] == keyboard_listing.listing_id
    assert result["composite_score"] is not None

    snapshot_count = db.query(models.PriceSnapshot).filter_by(listing_id=keyboard_listing.listing_id).count()
    assert snapshot_count == 1  # REQ-P2-2: appended, not overwritten

    score_count = db.query(models.DealScore).filter_by(listing_id=keyboard_listing.listing_id).count()
    assert score_count == 1


def test_refresh_appends_rather_than_overwrites_price_history(db, keyboard_listing):
    """REQ-P2-2."""
    refresh.refresh_listing(db, keyboard_listing)
    refresh.refresh_listing(db, keyboard_listing)

    snapshot_count = db.query(models.PriceSnapshot).filter_by(listing_id=keyboard_listing.listing_id).count()
    assert snapshot_count == 2


def test_watchlist_alert_respects_24h_throttle(db, keyboard_listing):
    """REQ-P5-3."""
    item = models.WatchlistItem(listing_id=keyboard_listing.listing_id, threshold_score=0)  # always crosses
    db.add(item)
    db.commit()

    deal_score = models.DealScore(listing_id=keyboard_listing.listing_id, composite_score=99)
    db.add(deal_score)
    db.flush()

    first = refresh.check_watchlist_threshold(db, keyboard_listing, deal_score)
    second = refresh.check_watchlist_threshold(db, keyboard_listing, deal_score)

    assert first is True
    assert second is False  # throttled — already alerted within 24h
