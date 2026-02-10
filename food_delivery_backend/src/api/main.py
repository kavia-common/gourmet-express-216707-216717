from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.db.session import engine

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
]

app = FastAPI(
    title="Gourmet Express Backend",
    description="FastAPI backend for a food delivery application (restaurants, menus, orders, payments, deliveries).",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_db_smoke_test() -> None:
    """
    On startup, perform a lightweight DB connectivity check.

    This does not create tables; it simply validates that DATABASE_URL / db_connection.txt points
    to a reachable PostgreSQL instance.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


@app.get("/", tags=["health"], summary="Health check")
def health_check():
    """Return a simple health response."""
    return {"message": "Healthy"}
