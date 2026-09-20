from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, models
from ..database import get_db

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _get_listing_or_404(listing_id: int, db: Session) -> models.Listing:
    listing = crud.get_listing(db, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/{listing_id}/price-history", response_model=List[schemas.PriceSnapshotOut])
def get_price_history(listing_id: int, db: Session = Depends(get_db)):
    """REQ-P6-1 (feeds the future chart) — here as the raw data endpoint."""
    _get_listing_or_404(listing_id, db)
    return (
        db.query(models.PriceSnapshot)
        .filter(models.PriceSnapshot.listing_id == listing_id)
        .order_by(models.PriceSnapshot.recorded_at.asc())
        .all()
    )


@router.get("/{listing_id}/deal-score", response_model=schemas.DealScoreOut)
def get_latest_deal_score(listing_id: int, db: Session = Depends(get_db)):
    _get_listing_or_404(listing_id, db)
    score = (
        db.query(models.DealScore)
        .filter(models.DealScore.listing_id == listing_id)
        .order_by(models.DealScore.computed_at.desc())
        .first()
    )
    if score is None:
        raise HTTPException(status_code=404, detail="No deal score computed yet for this listing")
    return score


@router.get("/{listing_id}/review-signals", response_model=List[schemas.ReviewSignalOut])
def get_review_signals(listing_id: int, db: Session = Depends(get_db)):
    _get_listing_or_404(listing_id, db)
    return (
        db.query(models.ReviewSignal)
        .filter(models.ReviewSignal.listing_id == listing_id)
        .order_by(models.ReviewSignal.mention_count.desc())
        .all()
    )
