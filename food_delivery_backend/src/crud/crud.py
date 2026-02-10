from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.models import (
    Delivery,
    DeliveryStatusHistory,
    MenuItem,
    Order,
    OrderItem,
    Payment,
    Restaurant,
    User,
)


def _money_sum(values: list[Decimal]) -> Decimal:
    total = Decimal("0.00")
    for v in values:
        total += v
    return total


# PUBLIC_INTERFACE
def create_user(db: Session, *, email: str, name: str, role: str = "customer", hashed_password: Optional[str] = None) -> User:
    """Create and persist a user."""
    user = User(email=email, name=name, role=role, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# PUBLIC_INTERFACE
def get_user_by_email(db: Session, *, email: str) -> Optional[User]:
    """Fetch a user by email."""
    return db.scalar(select(User).where(User.email == email))


# PUBLIC_INTERFACE
def list_restaurants(db: Session) -> list[Restaurant]:
    """List restaurants."""
    return list(db.scalars(select(Restaurant).order_by(Restaurant.name)))


# PUBLIC_INTERFACE
def get_restaurant(db: Session, *, restaurant_id: int) -> Optional[Restaurant]:
    """Get restaurant by id."""
    return db.get(Restaurant, restaurant_id)


# PUBLIC_INTERFACE
def list_menu_items_for_restaurant(db: Session, *, restaurant_id: int, only_available: bool = True) -> list[MenuItem]:
    """List menu items for a restaurant."""
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    if only_available:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    stmt = stmt.order_by(MenuItem.name)
    return list(db.scalars(stmt))


# PUBLIC_INTERFACE
def get_menu_item(db: Session, *, menu_item_id: int) -> Optional[MenuItem]:
    """Get menu item by id."""
    return db.get(MenuItem, menu_item_id)


# PUBLIC_INTERFACE
def create_order(
    db: Session,
    *,
    user_id: int,
    restaurant_id: int,
    delivery_address: Optional[str],
    items: list[dict],
) -> Order:
    """Create an order and its items.

    items: list of dicts: {menu_item_id: int, quantity: int}
    """
    order = Order(user_id=user_id, restaurant_id=restaurant_id, delivery_address=delivery_address, status="created", total_amount=Decimal("0.00"))
    db.add(order)
    db.flush()  # get order.id before adding items

    order_items: list[OrderItem] = []
    line_totals: list[Decimal] = []

    for item in items:
        menu_item = db.get(MenuItem, item["menu_item_id"])
        if menu_item is None:
            raise ValueError(f"Menu item {item['menu_item_id']} not found")

        qty = int(item.get("quantity", 1))
        if qty < 1:
            raise ValueError("Quantity must be >= 1")

        unit_price = Decimal(menu_item.price)
        line_total = unit_price * qty

        oi = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=qty,
            unit_price=unit_price,
            line_total=line_total,
        )
        order_items.append(oi)
        line_totals.append(line_total)

    order.total_amount = _money_sum(line_totals)
    db.add_all(order_items)

    db.commit()
    db.refresh(order)
    return order


# PUBLIC_INTERFACE
def get_order(db: Session, *, order_id: int) -> Optional[Order]:
    """Get order by id."""
    return db.get(Order, order_id)


# PUBLIC_INTERFACE
def set_order_status(db: Session, *, order_id: int, status: str) -> Order:
    """Update order status."""
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError("Order not found")
    order.status = status
    db.commit()
    db.refresh(order)
    return order


# PUBLIC_INTERFACE
def upsert_payment_for_order(
    db: Session,
    *,
    order_id: int,
    provider: str,
    amount: Decimal,
    status: str = "pending",
    provider_payment_id: Optional[str] = None,
    raw_payload: Optional[str] = None,
) -> Payment:
    """Create or update a payment record for an order."""
    payment = db.scalar(select(Payment).where(Payment.order_id == order_id))
    if payment is None:
        payment = Payment(order_id=order_id, provider=provider, amount=amount, status=status, provider_payment_id=provider_payment_id, raw_payload=raw_payload)
        db.add(payment)
    else:
        payment.provider = provider
        payment.amount = amount
        payment.status = status
        payment.provider_payment_id = provider_payment_id
        payment.raw_payload = raw_payload

    db.commit()
    db.refresh(payment)
    return payment


# PUBLIC_INTERFACE
def create_delivery(db: Session, *, order_id: int, delivery_person_id: Optional[int] = None, eta_minutes: Optional[int] = None) -> Delivery:
    """Create delivery for an order (one-to-one)."""
    delivery = Delivery(order_id=order_id, delivery_person_id=delivery_person_id, eta_minutes=eta_minutes, status="assigned" if delivery_person_id else "unassigned")
    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    # Add initial status history
    hist = DeliveryStatusHistory(delivery_id=delivery.id, status=delivery.status, note="Initial status")
    db.add(hist)
    db.commit()
    return delivery


# PUBLIC_INTERFACE
def set_delivery_status(db: Session, *, delivery_id: int, status: str, note: Optional[str] = None) -> Delivery:
    """Update delivery status and append to history."""
    delivery = db.get(Delivery, delivery_id)
    if delivery is None:
        raise ValueError("Delivery not found")

    delivery.status = status
    db.add(DeliveryStatusHistory(delivery_id=delivery_id, status=status, note=note))
    db.commit()
    db.refresh(delivery)
    return delivery
