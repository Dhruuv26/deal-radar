from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/categories", response_model=List[schemas.CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


@router.get("/retailers", response_model=List[schemas.RetailerOut])
def list_retailers(db: Session = Depends(get_db)):
    return crud.get_retailers(db)


@router.get("/products/search", response_model=List[schemas.ProductSearchResult])
def search_products(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    """REQ-P1-1."""
    return crud.search_products(db, q)


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/products", response_model=schemas.ProductOut, status_code=201)
def add_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    """REQ-P1-2, REQ-P1-3, REQ-P1-4."""
    if crud.get_category(db, payload.category_id) is None:
        raise HTTPException(status_code=400, detail=f"Category id {payload.category_id} does not exist.")

    try:
        return crud.create_product_with_listing(db, payload)
    except crud.UnsupportedRetailerError as e:
        # REQ-P1-3: explanatory message for an unsupported retailer, not a raw failure.
        raise HTTPException(status_code=400, detail=str(e))
    except crud.DuplicateListingError as e:
        # REQ-P1-4: reject duplicate retailer SKU entries.
        raise HTTPException(status_code=409, detail=str(e))
