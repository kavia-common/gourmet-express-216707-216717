from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from src.api.config import get_payment_webhook_secret
from src.crud import crud
from src.db.session import get_db
from src.schemas.schemas import (
    MockPaymentIntentCreate,
    MockPaymentIntentRead,
    PaymentRead,
    PaymentWebhookEvent,
)

router = APIRouter(prefix="/payments", tags=["payments"])


def _ensure_decimal(v: Decimal | None, fallback: Decimal) -> Decimal:
    return v if v is not None else fallback


@router.post(
    "/mock/intent",
    response_model=MockPaymentIntentRead,
    summary="Create a mock payment intent for an order",
    description="Creates/updates a payment record for an order and returns a mock checkout URL. This is for UI simulation only.",
    operation_id="create_mock_payment_intent__payments__mock__intent_post",
)
def create_mock_payment_intent(payload: MockPaymentIntentCreate, db: Session = Depends(get_db)) -> MockPaymentIntentRead:
    """Create a mock payment intent and persist a Payment row."""
    order = crud.get_order(db, order_id=payload.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    amount = _ensure_decimal(payload.amount, Decimal(order.total_amount))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be > 0")

    provider_payment_id = f"mock_{uuid4().hex}"
    status = "authorized" if payload.succeed else "failed"

    payment = crud.upsert_payment_for_order(
        db,
        order_id=payload.order_id,
        provider=payload.provider,
        amount=amount,
        status=status,
        provider_payment_id=provider_payment_id,
        raw_payload=json.dumps(
            {
                "currency": payload.currency,
                "succeed": payload.succeed,
                "generated_by": "mock_intent",
            }
        ),
    )

    # Also nudge order status forward when authorized (simple happy-path)
    if status == "authorized" and order.status == "created":
        crud.set_order_status(db, order_id=order.id, status="confirmed")

    checkout_url = f"/mock-checkout?provider={payload.provider}&payment_id={provider_payment_id}&order_id={order.id}"

    return MockPaymentIntentRead(
        payment=PaymentRead.model_validate(payment),
        checkout_url=checkout_url,
        provider_payment_id=provider_payment_id,
    )


@router.post(
    "/webhooks/mock",
    summary="Receive mock provider webhook",
    description="Receives mock payment webhooks. Validates X-Webhook-Secret and updates payment + order status.",
    operation_id="mock_payment_webhook__payments__webhooks__mock_post",
)
async def mock_payment_webhook(
    request: Request,
    event: PaymentWebhookEvent,
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
    db: Session = Depends(get_db),
) -> dict:
    """Process a mock payment webhook event."""
    expected = get_payment_webhook_secret()
    if not x_webhook_secret or x_webhook_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payment = crud.get_payment_by_provider_payment_id(db, provider_payment_id=event.provider_payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found for provider_payment_id")

    if payment.order_id != event.order_id:
        raise HTTPException(status_code=400, detail="order_id mismatch for this payment")

    raw_body = await request.body()
    raw_payload = None
    try:
        raw_payload = raw_body.decode("utf-8")
    except Exception:
        raw_payload = None

    # Update payment status and payload
    payment = crud.upsert_payment_for_order(
        db,
        order_id=event.order_id,
        provider=event.provider,
        amount=Decimal(payment.amount),
        status=event.status,
        provider_payment_id=event.provider_payment_id,
        raw_payload=raw_payload or json.dumps({"event": event.model_dump()}),
    )

    # Update order status based on payment status (simple mapping)
    if event.status in ("authorized", "captured"):
        order = crud.set_order_status(db, order_id=event.order_id, status="confirmed")
        return {"ok": True, "payment_id": payment.id, "order_id": order.id, "order_status": order.status}

    if event.status in ("failed",):
        order = crud.set_order_status(db, order_id=event.order_id, status="cancelled")
        return {"ok": True, "payment_id": payment.id, "order_id": order.id, "order_status": order.status}

    return {"ok": True, "payment_id": payment.id}


@router.post(
    "/mock/simulate-webhook",
    summary="Simulate sending a webhook back into this backend",
    description="Utility endpoint for local/dev: posts a webhook event to /payments/webhooks/mock using the configured secret.",
    operation_id="simulate_mock_webhook__payments__mock__simulate_webhook_post",
)
async def simulate_mock_webhook(event: PaymentWebhookEvent) -> dict:
    """Simulate a webhook call to this same service."""
    secret = get_payment_webhook_secret()

    # Use a relative URL; in local usage, the frontend/dev can call backend directly.
    # For containerized setups, the orchestrator typically routes to the service base URL.
    webhook_url = "http://localhost:8000/payments/webhooks/mock"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            webhook_url,
            headers={"X-Webhook-Secret": secret},
            json=event.model_dump(),
        )
        return {"sent_to": webhook_url, "status_code": resp.status_code, "response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text}
