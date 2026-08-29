from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import products

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Deal Radar API",
    description="Price-tracking and deal-scoring API for computer peripherals. "
                 "This build implements P1 (Product Search & Catalog Management) "
                 "only — see README for the full implementation-status breakdown.",
    version="0.3.0",  # ~30% of the planned six-feature system
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)


@app.get("/")
def root():
    return {"service": "Deal Radar API", "status": "ok"}
