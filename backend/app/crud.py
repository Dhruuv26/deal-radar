"""
Database operations for P1: Product Search & Catalog Management.

Each function is annotated with the SRS requirement it implements so the
mapping from spec to code stays traceable.
"""
from sqlalchemy.orm import Session
from sqlalchemy import or_

from . import models, schemas


def get_categories(db: Session):
    return db.query(models.Category).all()


def get_retailers(db: Session):
    return db.query(models.Retailer).all()


def get_retailer(db: Session, retailer_id: int):
    return db.query(models.Retailer).filter(models.Retailer.retailer_id == retailer_id).first()


def get_category(db: Session, category_id: int):
    return db.query(models.Category).filter(models.Category.category_id == category_id).first()


def search_products(db: Session, query: str):
    """REQ-P1-1: search tracked peripherals by product name or brand."""
    like_pattern = f"%{query}%"
    products = (
        db.query(models.Product)
        .filter(or_(models.Product.name.ilike(like_pattern), models.Product.brand.ilike(like_pattern)))
        .all()
    )
    return [
        schemas.ProductSearchResult(
            product_id=p.product_id,
            name=p.name,
            brand=p.brand,
            category_name=p.category.name,
            listing_count=len(p.listings),
        )
        for p in products
    ]


def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.product_id == product_id).first()


def find_duplicate_listing(db: Session, retailer_id: int, retailer_sku: str):
    """REQ-P1-4: prevent duplicate listing entries for the same retailer SKU."""
    return (
        db.query(models.Listing)
        .filter(
            models.Listing.retailer_id == retailer_id,
            models.Listing.retailer_sku == retailer_sku,
        )
        .first()
    )


class UnsupportedRetailerError(Exception):
    """Raised when a listing references a retailer_id that isn't registered.

    Maps to REQ-P1-3: the API layer turns this into a 4xx response with an
    explanatory message rather than a raw 500 error.
    """


class DuplicateListingError(Exception):
    """Raised when a listing already exists for that retailer_id + SKU (REQ-P1-4)."""


def create_product_with_listing(db: Session, payload: schemas.ProductCreate) -> models.Product:
    """REQ-P1-2: add a new product to track by supplying a retailer listing."""
    retailer = get_retailer(db, payload.listing.retailer_id)
    if retailer is None:
        raise UnsupportedRetailerError(
            f"Retailer id {payload.listing.retailer_id} is not a supported data source."
        )

    if find_duplicate_listing(db, payload.listing.retailer_id, payload.listing.retailer_sku):
        raise DuplicateListingError(
            f"A listing for SKU '{payload.listing.retailer_sku}' at this retailer is already tracked."
        )

    product = models.Product(
        name=payload.name,
        brand=payload.brand,
        category_id=payload.category_id,
    )
    db.add(product)
    db.flush()  # populate product.product_id before creating the listing

    listing = models.Listing(
        product_id=product.product_id,
        retailer_id=payload.listing.retailer_id,
        retailer_sku=payload.listing.retailer_sku,
        product_url=payload.listing.product_url,
    )
    db.add(listing)
    db.commit()
    db.refresh(product)
    return product
