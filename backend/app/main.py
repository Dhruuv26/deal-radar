from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .database import Base, engine
from .routers import products, listings, watchlist, ingestion
from .services import scheduler as scheduler_service

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skipped under pytest so test runs don't spin up a background job.
    if os.environ.get("PYTEST_CURRENT_TEST") is None:
        scheduler_service.start_scheduler()
    yield
    scheduler_service.stop_scheduler()


app = FastAPI(
    title="Deal Radar API",
    description="Price-tracking and deal-scoring API for computer peripherals. "
                 "This build implements P1-P5 (catalog, ingestion, true price / "
                 "deal score, review signals, watchlist). P6 (dashboard UI) is "
                 "the remaining increment — see README.",
    version="0.7.0",  # ~70% of the planned six-feature system
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite dev server, either hostname
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(listings.router)
app.include_router(watchlist.router)
app.include_router(ingestion.router)


@app.get("/")
def root():
    return {"service": "Deal Radar API", "status": "ok"}
