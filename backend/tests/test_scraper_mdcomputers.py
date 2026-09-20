"""
Tests for the MD Computers scraper. These test the PARSING logic against a
saved HTML fixture (built from a real product page fetched during
development) and the robots.txt gating logic with a mocked RobotFileParser
— neither hits the live network, since this sandbox can't reach
mdcomputers.in and tests should be deterministic and offline regardless.

See scraper_mdcomputers.py's module docstring: the actual end-to-end fetch
has NOT been execution-tested against the live site and should be run
once manually (`python -m app.services.scraper_mdcomputers`) before relying
on it for real.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services import scraper_mdcomputers as scraper

# A trimmed but structurally faithful fixture, based on the real
# mdcomputers.in/product/aula-f2023-gaming-keyboard page fetched while
# building this scraper — same meta tag, same offer phrasing, same
# "no reviews yet" review section.
SAMPLE_PRODUCT_PAGE_HTML = """
<html>
<head>
  <meta property="og:title" content="Aula F2023 Membrane Gaming Keyboard" />
  <meta property="product:price:amount" content="820.00" />
  <meta property="product:price:currency" content="INR" />
</head>
<body>
  <h1>Aula F2023 Membrane Gaming Keyboard</h1>
  <p>7.5% Instant Discount or Up To Rs. 2000 on order of Rs. 10,000 and above with HDFC Credit Card EMI.</p>
  <div id="tab-review">
    <p>No reviews yet.</p>
  </div>
</body>
</html>
"""

SAMPLE_PAGE_MISSING_PRICE_HTML = """
<html><head><meta property="og:title" content="Some Product" /></head><body></body></html>
"""


def test_parse_product_page_extracts_price():
    result = scraper.parse_product_page(SAMPLE_PRODUCT_PAGE_HTML)
    assert result["listed_price"] == 820.00


def test_parse_product_page_extracts_offer_text():
    result = scraper.parse_product_page(SAMPLE_PRODUCT_PAGE_HTML)
    assert "Instant Discount" in result["offer_text"]


def test_parse_product_page_raises_when_price_missing():
    with pytest.raises(scraper.ScraperParseError):
        scraper.parse_product_page(SAMPLE_PAGE_MISSING_PRICE_HTML)


def test_robots_disallowed_blocks_fetch():
    """REQ-P2-5: a disallowed path must never be fetched."""
    fake_rp = MagicMock()
    fake_rp.can_fetch.return_value = False

    with patch.object(scraper, "_get_robot_parser", return_value=fake_rp):
        with pytest.raises(scraper.ScraperBlockedByRobotsError):
            scraper._check_robots_allowed("https://mdcomputers.in/some-disallowed-path")


def test_robots_allowed_passes_through():
    fake_rp = MagicMock()
    fake_rp.can_fetch.return_value = True

    with patch.object(scraper, "_get_robot_parser", return_value=fake_rp):
        scraper._check_robots_allowed("https://mdcomputers.in/product/aula-f2023-gaming-keyboard")
        # no exception raised = pass
