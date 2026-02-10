from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.api.config import get_cors_allow_origins
from src.api.deliveries import router as deliveries_router
from src.api.payments import router as payments_router
from src.db.session import engine

openapi_tags = [
    {"name": "health", "description": "Service health and diagnostics."},
    {"name": "deliveries", "description": "Delivery assignment and tracking endpoints."},
    {"name": "payments", "description": "Mock payment intents and webhook processing."},
]

app = FastAPI(
    title="Gourmet Express Backend",
    description="FastAPI backend for a food delivery application (restaurants, menus, orders, payments, deliveries).",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# Step 4.1 env wiring: make CORS configurable to support container integration.
allow_origins = get_cors_allow_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(deliveries_router)
app.include_router(payments_router)


@app.on_event("startup")
def _startup_db_smoke_test() -> None:
    """
    On startup, perform a lightweight DB connectivity check.

    This does not create tables; it simply validates that DATABASE_URL / db_connection.txt points
    to a reachable PostgreSQL instance.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check__get")
def health_check():
    """Return a simple health response."""
    return {"message": "Healthy"}
