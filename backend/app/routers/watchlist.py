from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=List[schemas.WatchlistOut])
def list_watchlist(db: Session = Depends(get_db)):
    return crud.get_watchlist(db)


@router.post("", response_model=schemas.WatchlistOut, status_code=201)
def add_watchlist_item(payload: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    """REQ-P5-1, REQ-P5-2."""
    try:
        return crud.add_to_watchlist(db, payload.listing_id, payload.threshold_score)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except crud.DuplicateWatchlistItemError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{watchlist_id}", status_code=204)
def remove_watchlist_item(watchlist_id: int, db: Session = Depends(get_db)):
    """REQ-P5-1."""
    if not crud.remove_from_watchlist(db, watchlist_id):
        raise HTTPException(status_code=404, detail="Watchlist item not found")
