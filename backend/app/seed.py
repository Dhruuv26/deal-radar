"""
Seeds the categories (REQ-P4-1's 7 peripheral categories, used from P1
onward for classification) and the two officially-supported retailers
(SRS Section 2.5 — Amazon and Flipkart via official APIs).

Run once after creating a fresh database:
    python -m app.seed
"""
from .database import SessionLocal, engine, Base
from . import models

CATEGORIES = ["keyboard", "mouse", "monitor", "webcam", "headset", "printer", "storage"]
RETAILERS = [("Amazon.in", True), ("Flipkart", True)]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.Category).count() == 0:
            db.add_all([models.Category(name=c) for c in CATEGORIES])
        if db.query(models.Retailer).count() == 0:
            db.add_all([models.Retailer(name=n, has_api=a) for n, a in RETAILERS])
        db.commit()
        print("Seed complete:", db.query(models.Category).count(), "categories,",
              db.query(models.Retailer).count(), "retailers.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
