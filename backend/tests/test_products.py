"""
Smoke tests for the P1 endpoints. Each test is tied to the SRS requirement
it verifies. This is intentionally a small suite for the 30% checkpoint —
broader coverage is planned alongside each future increment (see WBS,
Phase 7: Testing).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app import models

# Isolated in-memory DB per test run, so tests never touch deal_radar.db.
# StaticPool keeps the same connection (and therefore the same in-memory
# database) alive across the whole test session instead of creating a
# fresh, empty :memory: DB on every new connection.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(models.Category(category_id=1, name="keyboard"))
    db.add(models.Retailer(retailer_id=1, name="Amazon.in", has_api=True))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_search_returns_empty_when_no_products():
    """REQ-P1-1."""
    resp = client.get("/api/products/search", params={"q": "keyboard"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_add_product_and_search_finds_it():
    """REQ-P1-1 + REQ-P1-2."""
    payload = {
        "name": "EvoFox Ronin",
        "brand": "EvoFox",
        "category_id": 1,
        "listing": {
            "retailer_id": 1,
            "retailer_sku": "EVOFOX-RONIN-01",
            "product_url": "https://www.amazon.in/dp/EXAMPLE123",
        },
    }
    create_resp = client.post("/api/products", json=payload)
    assert create_resp.status_code == 201
    product_id = create_resp.json()["product_id"]

    search_resp = client.get("/api/products/search", params={"q": "Ronin"})
    assert search_resp.status_code == 200
    results = search_resp.json()
    assert len(results) == 1
    assert results[0]["product_id"] == product_id
    assert results[0]["listing_count"] == 1


def test_add_product_with_unsupported_retailer_is_rejected():
    """REQ-P1-3."""
    payload = {
        "name": "Some Mouse",
        "brand": "Generic",
        "category_id": 1,
        "listing": {
            "retailer_id": 999,  # does not exist
            "retailer_sku": "SKU-1",
            "product_url": "https://example.com/product",
        },
    }
    resp = client.post("/api/products", json=payload)
    assert resp.status_code == 400
    assert "not a supported data source" in resp.json()["detail"]


def test_duplicate_listing_is_rejected():
    """REQ-P1-4."""
    payload = {
        "name": "Cosmic Byte Kilimanjaro 2",
        "brand": "Cosmic Byte",
        "category_id": 1,
        "listing": {
            "retailer_id": 1,
            "retailer_sku": "CB-KILI-2",
            "product_url": "https://www.amazon.in/dp/CB2",
        },
    }
    first = client.post("/api/products", json=payload)
    assert first.status_code == 201

    # Same retailer + SKU again, even under a different product name
    payload["name"] = "Cosmic Byte Kilimanjaro 2 (re-listed)"
    second = client.post("/api/products", json=payload)
    assert second.status_code == 409
