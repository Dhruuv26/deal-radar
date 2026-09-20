from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import refresh as refresh_service

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


@router.post("/refresh-now", response_model=schemas.RefreshSummary)
def refresh_now(db: Session = Depends(get_db)):
    """
    Manually runs the same pipeline the scheduled job runs every 6 hours
    (REQ-P2-1). Exists because waiting for the real interval isn't
    practical for testing or demos.
    """
    results = refresh_service.refresh_all_listings(db)
    return schemas.RefreshSummary(
        listings_refreshed=len(results),
        alerts_triggered=sum(1 for r in results if r["alert_triggered"]),
        results=results,
    )
