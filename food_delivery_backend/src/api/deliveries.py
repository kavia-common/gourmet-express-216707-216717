from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.crud import crud
from src.db.session import get_db
from src.schemas.schemas import (
    DeliveryAssignRequest,
    DeliveryCreate,
    DeliveryRead,
    DeliveryStatusHistoryCreate,
    DeliveryStatusHistoryRead,
    DeliveryWithHistoryRead,
)

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.post(
    "",
    response_model=DeliveryRead,
    summary="Create a delivery record for an order",
    description="Create a delivery for an order (one-to-one). If delivery_person_id is provided, the delivery is immediately assigned.",
    operation_id="create_delivery__deliveries_post",
)
def create_delivery_endpoint(payload: DeliveryCreate, db: Session = Depends(get_db)) -> DeliveryRead:
    """Create a delivery record for a given order."""
    order = crud.get_order(db, order_id=payload.order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    existing = crud.get_delivery_by_order_id(db, order_id=payload.order_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Delivery already exists for this order")

    delivery = crud.create_delivery(
        db,
        order_id=payload.order_id,
        delivery_person_id=payload.delivery_person_id,
        eta_minutes=payload.eta_minutes,
    )
    return DeliveryRead.model_validate(delivery)


@router.get(
    "",
    response_model=list[DeliveryRead],
    summary="List deliveries",
    description="List deliveries; optionally filter by delivery_person_id for a delivery-person view.",
    operation_id="list_deliveries__deliveries_get",
)
def list_deliveries_endpoint(
    delivery_person_id: int | None = Query(None, description="Optional delivery person user_id to filter by."),
    db: Session = Depends(get_db),
) -> list[DeliveryRead]:
    """List deliveries (optionally filtered)."""
    deliveries = crud.list_deliveries(db, delivery_person_id=delivery_person_id)
    return [DeliveryRead.model_validate(d) for d in deliveries]


@router.get(
    "/{delivery_id}",
    response_model=DeliveryWithHistoryRead,
    summary="Get a delivery with its status history",
    operation_id="get_delivery__deliveries__delivery_id__get",
)
def get_delivery_endpoint(delivery_id: int, db: Session = Depends(get_db)) -> DeliveryWithHistoryRead:
    """Get a delivery and its status history."""
    delivery = crud.get_delivery_by_id(db, delivery_id=delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")

    history = crud.list_delivery_status_history(db, delivery_id=delivery_id)
    return DeliveryWithHistoryRead(
        delivery=DeliveryRead.model_validate(delivery),
        history=[DeliveryStatusHistoryRead.model_validate(h) for h in history],
    )


@router.post(
    "/{delivery_id}/assign",
    response_model=DeliveryRead,
    summary="Assign a delivery to a delivery person",
    operation_id="assign_delivery__deliveries__delivery_id__assign_post",
)
def assign_delivery_endpoint(delivery_id: int, payload: DeliveryAssignRequest, db: Session = Depends(get_db)) -> DeliveryRead:
    """Assign a delivery to a delivery person, updating status to 'assigned' if needed."""
    # Validate assignee exists and is delivery role (soft validation)
    user = db.get(crud.User, payload.delivery_person_id) if hasattr(crud, "User") else None  # defensive; should not happen
    if user is None:
        # fallback: check via direct model import path
        from src.models.models import User  # local import to avoid unused import when not needed

        user = db.get(User, payload.delivery_person_id)

    if user is None:
        raise HTTPException(status_code=404, detail="Delivery person not found")
    if getattr(user, "role", None) not in ("delivery", "admin"):
        raise HTTPException(status_code=400, detail="User is not a delivery person")

    try:
        delivery = crud.assign_delivery(
            db,
            delivery_id=delivery_id,
            delivery_person_id=payload.delivery_person_id,
            eta_minutes=payload.eta_minutes,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return DeliveryRead.model_validate(delivery)


@router.post(
    "/{delivery_id}/status",
    response_model=DeliveryRead,
    summary="Update delivery status",
    description="Update delivery status and append a status-history entry.",
    operation_id="set_delivery_status__deliveries__delivery_id__status_post",
)
def set_delivery_status_endpoint(
    delivery_id: int,
    payload: DeliveryStatusHistoryCreate,
    db: Session = Depends(get_db),
) -> DeliveryRead:
    """Update delivery status."""
    if payload.delivery_id != delivery_id:
        raise HTTPException(status_code=400, detail="delivery_id in body must match path parameter")

    try:
        delivery = crud.set_delivery_status(db, delivery_id=delivery_id, status=payload.status, note=payload.note)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return DeliveryRead.model_validate(delivery)
