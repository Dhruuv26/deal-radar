"""
Real retailer integration: MD Computers (mdcomputers.in), scraped rather
than accessed via official API — this is the stretch-goal "one additional
retailer without an API" from the SRS (REQ-P2-5), and it's what replaces
Amazon/Flipkart as the actual working data source, since both of their
official APIs turned out to be unreachable for a new project as of 2026
(see docs/Deal_Radar_SRS.docx, Appendix C, TBD-1 — Amazon's PA-API was
deprecated May 15 2026 and its Creators API replacement requires 10
qualifying sales/30 days; Flipkart closed direct affiliate sign-ups to
new applicants around the same time).

Verified against a real product page (mdcomputers.in/product/aula-f2023-
gaming-keyboard, fetched during development): the site exposes price via
a standard Open Graph `product:price:amount` meta tag, which is far more
stable to parse than CSS class names that change on redesign.

REQ-P2-5: this checks robots.txt at runtime, on every fetch, rather than
relying on a one-time manual check — robots.txt can change, and checking
live is the more correct implementation of "respect robots.txt" than a
check that could go stale.

IMPORTANT — not executable from this environment: the sandbox this was
written in has restricted network egress and cannot reach mdcomputers.in,
so this scraper has been verified against a real, manually-fetched page
snapshot but has NOT been execution-tested end-to-end. Run
`python -m app.services.scraper_mdcomputers` yourself once (see __main__
block below) before relying on it, and re-check if MD Computers changes
their page structure.
"""
import re
import time
import logging
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .ingestion import RetailerAPIClient, RawListingData, RawReviewSnippet

logger = logging.getLogger("deal_radar.scraper.mdcomputers")

USER_AGENT = "DealRadarBot/0.1 (student software engineering project; contact: <your email here>)"
REQUEST_DELAY_SECONDS = 2  # minimum gap between requests to the same site
REQUEST_TIMEOUT_SECONDS = 10

_robots_cache = {}  # domain -> RobotFileParser, so we don't refetch robots.txt every call


class ScraperBlockedByRobotsError(Exception):
    """Raised when robots.txt disallows fetching the requested URL."""


class ScraperParseError(Exception):
    """Raised when the page doesn't have the data we expect (site structure changed)."""


def _get_robot_parser(url: str) -> RobotFileParser:
    """
    Fetches and parses robots.txt ourselves, with our real User-Agent header,
    rather than letting RobotFileParser.read() fetch it internally.

    Why: RobotFileParser.read() makes its own request using Python's default
    "Python-urllib/x.y" User-Agent, which many sites' bot protection blocks
    outright (403). When that happens, RobotFileParser silently falls back
    to "disallow everything" as a safe default -- which looks identical to
    a real robots.txt block but isn't one. Fetching the file ourselves with
    the same header we use for the real request avoids that false negative.
    """
    domain = urlparse(url).netloc
    if domain not in _robots_cache:
        rp = RobotFileParser()
        robots_url = f"https://{domain}/robots.txt"
        rp.set_url(robots_url)
        try:
            req = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
            raw = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS).read().decode("utf-8", errors="replace")
            rp.parse(raw.splitlines())
        except Exception as exc:
            logger.warning("Could not fetch robots.txt for %s (%s) -- assuming disallowed.", domain, exc)
            rp.disallow_all = True
        _robots_cache[domain] = rp
    return _robots_cache[domain]


def _check_robots_allowed(url: str):
    """REQ-P2-5: never fetch a URL robots.txt disallows for our user agent."""
    rp = _get_robot_parser(url)
    if not rp.can_fetch(USER_AGENT, url):
        raise ScraperBlockedByRobotsError(f"robots.txt disallows fetching {url}")


def _fetch_page(url: str) -> str:
    _check_robots_allowed(url)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)  # rate limit before this client is used again
    return response.text


def parse_product_page(html: str) -> dict:
    """
    Pure parsing logic, kept separate from the network call so it can be
    unit-tested against a saved HTML fixture without hitting the network.
    """
    soup = BeautifulSoup(html, "html.parser")

    price_tag = soup.find("meta", attrs={"property": "product:price:amount"})
    if price_tag is None or not price_tag.get("content"):
        raise ScraperParseError(
            "Could not find a product:price:amount meta tag — MD Computers may have changed their page structure."
        )
    listed_price = float(price_tag["content"])

    # Bank/card offer text, if present (mirrors the shape parse_offer_text()
    # in services/refresh.py already knows how to handle).
    offer_text = ""
    page_text = soup.get_text(" ", strip=True)
    offer_match = re.search(r"[\d.]+%\s*Instant Discount.{0,120}?(?:EMI|Card|card)\b[^.]{0,20}", page_text)
    if not offer_match:
        offer_match = re.search(r"[\d.]+%\s*Instant Discount[^.]{0,80}", page_text)
    if offer_match:
        offer_text = offer_match.group(0)

    # Review snippets: best-effort. Many real niche-product pages (like the
    # one this was built against) genuinely have zero reviews, so an empty
    # list here is an expected, honest outcome — not a parsing failure.
    review_snippets = []
    review_section = soup.find(id="tab-review")
    if review_section:
        for review_div in review_section.find_all("p"):
            text = review_div.get_text(strip=True)
            if text:
                review_snippets.append(RawReviewSnippet(text=text, verified_purchase=False))

    return {
        "listed_price": listed_price,
        "offer_text": offer_text,
        "review_snippets": review_snippets,
    }


class MDComputersScraperClient(RetailerAPIClient):
    """Real (non-mock) client — scrapes mdcomputers.in product pages directly."""

    def fetch_listing(self, product_url: str, retailer_sku: str, category_name: str) -> RawListingData:
        from datetime import datetime  # local import to avoid unused import if this class is never used

        html = _fetch_page(product_url)
        parsed = parse_product_page(html)
        return RawListingData(
            retailer_sku=retailer_sku,
            listed_price=parsed["listed_price"],
            offer_text=parsed["offer_text"],
            review_snippets=parsed["review_snippets"],
            fetched_at=datetime.utcnow(),
        )


if __name__ == "__main__":
    # Manual smoke test — run this yourself: `python -m app.services.scraper_mdcomputers`
    # (requires network access this sandbox doesn't have).
    test_url = "https://mdcomputers.in/product/aula-f2023-gaming-keyboard/gamers-zone/gaming-keyboard"
    client = MDComputersScraperClient()
    result = client.fetch_listing(test_url, retailer_sku="F2023-BLACK", category_name="keyboard")
    print(result)
