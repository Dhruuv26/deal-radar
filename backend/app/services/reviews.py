"""
P4: Review Signal Analysis.

Implements REQ-P4-1 (per-category keyword dictionary), REQ-P4-2 (mention
counting with verified-purchase weighting), and REQ-P4-3 (only aggregated
counts are ever stored — never verbatim review text; note that
ReviewSignal, per models.py, has no text column at all, so this isn't just
a runtime choice, it's enforced by the schema).

Each keyword is tagged with a polarity (+1 = positive signal, -1 = a
complaint) so services/pricing.py can turn the aggregated counts into a
single review_score without re-reading any review text itself.
"""
from sqlalchemy.orm import Session
from typing import List

from . import ingestion
from .. import models

# category_name -> [(keyword phrase, polarity), ...]
# Deliberately short lists for this checkpoint (REQ-P4-1 requires *a*
# dictionary per category, not an exhaustive one) — see SRS Appendix C,
# TBD-3 for the plan to expand these.
CATEGORY_KEYWORDS = {
    "keyboard": [
        ("keycap wobble", -1),
        ("mushy", -1),
        ("backlight uneven", -1),
        ("solid build", 1),
        ("great typing", 1),
    ],
    "mouse": [
        ("sensor lag", -1),
        ("stopped responding", -1),
        ("scroll wheel", 1),
        ("comfortable", 1),
    ],
    "monitor": [
        ("backlight bleed", -1),
        ("ghosting", -1),
        ("wobbles", -1),
        ("color accuracy", 1),
        ("great panel", 1),
    ],
    "webcam": [
        ("autofocus hunting", -1),
        ("background noise", -1),
        ("sharp", 1),
    ],
    "headset": [
        ("uncomfortable", -1),
        ("boomy", -1),
        ("mic clarity", 1),
    ],
    "printer": [
        ("paper jam", -1),
        ("smudge", -1),
        ("crisp", 1),
    ],
    "storage": [
        ("loose", -1),
        ("advertised spec", 1),
        ("reliable", 1),
    ],
}

VERIFIED_WEIGHT = 2  # REQ-P4-2: verified-purchase mentions count double
UNVERIFIED_WEIGHT = 1


def extract_review_signals(
    db: Session, listing: models.Listing, review_snippets: List[ingestion.RawReviewSnippet]
) -> List[models.ReviewSignal]:
    """
    REQ-P4-1, REQ-P4-2: match review text against the listing's category
    keyword dictionary, weighting verified-purchase snippets more heavily,
    and persist only the aggregated counts (REQ-P4-3).

    Re-computes from scratch on every call — existing ReviewSignal rows for
    this listing are replaced rather than incremented, since each refresh
    represents the current full set of fetched reviews, not a delta.
    """
    category_name = listing.product.category.name
    keywords = CATEGORY_KEYWORDS.get(category_name, [])

    # Clear any signals from a previous refresh for this listing.
    db.query(models.ReviewSignal).filter(models.ReviewSignal.listing_id == listing.listing_id).delete()

    counts = {keyword: 0 for keyword, _ in keywords}
    for snippet in review_snippets:
        text_lower = snippet.text.lower()
        weight = VERIFIED_WEIGHT if snippet.verified_purchase else UNVERIFIED_WEIGHT
        for keyword, _polarity in keywords:
            if keyword in text_lower:
                counts[keyword] += weight

    signals = []
    for keyword, count in counts.items():
        if count > 0:
            signal = models.ReviewSignal(
                listing_id=listing.listing_id, keyword_tag=keyword, mention_count=count
            )
            db.add(signal)
            signals.append(signal)

    db.flush()
    return signals


def compute_review_score(listing: models.Listing) -> float:
    """
    Turns this listing's current ReviewSignal rows into a single 0-100
    score: start at neutral (50), add for positive-keyword mentions,
    subtract for negative-keyword mentions, clamp to [0, 100].
    """
    category_name = listing.product.category.name
    polarity_by_keyword = dict(CATEGORY_KEYWORDS.get(category_name, []))

    score = 50.0
    for signal in listing.review_signals:
        polarity = polarity_by_keyword.get(signal.keyword_tag, 0)
        score += polarity * signal.mention_count * 5  # each weighted mention moves the score by 5

    return max(0.0, min(100.0, score))
