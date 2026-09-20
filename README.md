# Deal Radar

Price-tracking and deal-scoring platform for computer peripherals sold on Indian
e-commerce sites. Built as a solo Software Engineering course project using an
**Incremental process model** — see `docs/Deal_Radar_SRS.docx` for the full
requirements and `docs/deal_radar_wbs.xml` for the phase breakdown.

## Implementation status: ~70% (P1-P5 complete, P6 remaining)

This checkpoint implements **P1 through P5 end to end** — catalog management,
a fully wired ingestion pipeline, true-price and deal-score computation,
category-specific review signal extraction, and watchlist management with
threshold-based alert logic. **P6 (dashboard/comparison UI)** is the one
remaining increment.

| Feature (SRS §4) | Status |
|---|---|
| P1 — Product Search & Catalog Management | ✅ Implemented (REQ-P1-1 .. REQ-P1-4) |
| P2 — Retailer Data Ingestion | ✅ Pipeline fully wired (REQ-P2-1 .. REQ-P2-5); data source is still mocked, see below |
| P3 — True Price & Deal Score Computation | ✅ Implemented (REQ-P3-1 .. REQ-P3-4) |
| P4 — Review Signal Analysis | ✅ Implemented (REQ-P4-1 .. REQ-P4-3) |
| P5 — Watchlist & Alerts | 🟡 CRUD + threshold logic done (REQ-P5-1 .. REQ-P5-3); alert *delivery* channel still TBD (SRS TBD-2) |
| P6 — Dashboard & Comparison | ⬜ Not started — only a single-listing detail view exists, no charts or side-by-side comparison yet |

**Why P2's data source is still mocked:** Amazon PA-API access depends on
affiliate approval that's still pending (SRS Appendix C, TBD-1). The
*pipeline* around it — scheduling, persistence, offer parsing, hookup to
P3/P4/P5 — is fully built and tested against `MockRetailerClient`, which
returns realistic randomized prices, offer text, and category-appropriate
review snippets. Swapping in a real `RetailerAPIClient` subclass once API
access is confirmed requires no changes anywhere else in the system — every
downstream piece depends only on the `RawListingData` shape.

**Why P5's alerts aren't delivered anywhere:** the notification channel
(email vs. SMS) is still an open decision (SRS TBD-2). `check_watchlist_threshold()`
correctly determines *whether* an alert should fire, respecting the
24-hour throttle (REQ-P5-3), and records that it fired — it just doesn't
send anything anywhere yet, since there's no channel to send it through.

## What actually runs

- **P2 pipeline**: `POST /api/ingestion/refresh-now` runs the full six-step
  cycle for every tracked listing (fetch → parse offers → compute true price →
  extract review signals → compute deal score → check watchlist), exactly
  matching the DFD's Level 2 (P2) decomposition. The same cycle also runs
  automatically every 6 hours via APScheduler (REQ-P2-1).
- **P3**: `true_price` and a genuine/not-genuine flag are computed from a
  30-day rolling median baseline (REQ-P3-1, REQ-P3-2) and combined with the
  review score into a 0-100 composite deal score (REQ-P3-3), recomputed on
  every refresh (REQ-P3-4).
- **P4**: category-specific keyword dictionaries (`services/reviews.py`)
  match against fetched review snippets, weight verified-purchase mentions
  2x (REQ-P4-2), and store only aggregated counts — never review text
  (REQ-P4-3, enforced by the schema itself, not just application logic).
- **P5**: add/remove a listing on the watchlist with a target deal-score
  threshold; the pipeline checks it on every refresh.

## Project structure

```
deal-radar/
├── docs/                    # ER diagram, use case diagrams, DFDs, sequence,
│                            # activity, and state diagrams (StarUML .mdj),
│                            # WBS, and the full SRS
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entrypoint + scheduler lifespan
│   │   ├── database.py      # SQLAlchemy engine/session
│   │   ├── models.py        # ORM models (all 8 ERD entities + WatchlistItem)
│   │   ├── schemas.py       # Pydantic request/response schemas
│   │   ├── crud.py          # P1 + P5 database operations
│   │   ├── seed.py          # seeds categories + retailers
│   │   ├── routers/
│   │   │   ├── products.py    # P1 endpoints
│   │   │   ├── listings.py    # P3/P4 endpoints (price history, deal score, review signals)
│   │   │   ├── watchlist.py   # P5 endpoints
│   │   │   └── ingestion.py   # manual refresh-now trigger
│   │   └── services/
│   │       ├── ingestion.py   # P2 interface + mock client
│   │       ├── refresh.py     # orchestrates P2->P3->P4->P5 for one cycle
│   │       ├── pricing.py     # P3: true price + deal score
│   │       ├── reviews.py     # P4: keyword dictionaries + extraction
│   │       └── scheduler.py   # APScheduler wiring (REQ-P2-1)
│   ├── tests/
│   │   ├── test_products.py         # REQ-P1-1 .. REQ-P1-4
│   │   └── test_refresh_pipeline.py # REQ-P2, REQ-P3, REQ-P4, REQ-P5
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api.js
        └── components/
            ├── SearchAddProduct.jsx   # P1 screen
            └── ListingDetail.jsx      # P3/P4/P5 screen (price history, deal
                                       # score, review signals, watchlist)
```

## Running it

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
python -m app.seed              # creates deal_radar.db, seeds categories + retailers
uvicorn app.main:app --reload
```

API docs (auto-generated by FastAPI) are then at `http://127.0.0.1:8000/docs`.
The scheduler starts automatically and refreshes every tracked listing every
6 hours; to see results immediately instead of waiting, call:

```bash
curl -X POST http://127.0.0.1:8000/api/ingestion/refresh-now
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Search for a tracked product, click **View
details**, then **Refresh price & deal data now** to see price history, deal
score, and review signals populate live.

### Tests

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

18 tests, covering REQ-P1 through REQ-P5.

## Analysis models

All diagrams referenced in the SRS are in `docs/` as StarUML project files:
- `deal_radar_erd.mdj` — Entity-Relationship Diagram
- `deal_radar_usecases.mdj` — Use Case Diagrams (main + sub-diagrams)
- `deal_radar_dfd.mdj` — Data Flow Diagrams (Context, Level 1, Level 2)
- `deal_radar_sequences.mdj` — Sequence diagrams for the main flows
- `deal_radar_activities.mdj` — Activity diagrams for the main flows
- `deal_radar_statecharts.mdj` — Listing lifecycle state machine
- `deal_radar_wbs.xml` — Work Breakdown Structure (open in ProjectLibre)

## Next increment: P6 — Dashboard & Comparison

The only feature left. Per the WBS:
- Price-history **chart** (currently a plain list in `ListingDetail.jsx`) — REQ-P6-1
- Side-by-side **comparison view** for 2-4 listings — REQ-P6-2
- Best-deal **highlighting** in the comparison view — REQ-P6-3

Everything P6 needs already exists behind the API (`/price-history`,
`/deal-score`, `/review-signals` per listing), so this increment is
frontend-only — no backend changes anticipated.
