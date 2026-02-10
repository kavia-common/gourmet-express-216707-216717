from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="customer")  # customer/admin/delivery
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")
    deliveries: Mapped[list["Delivery"]] = relationship("Delivery", back_populates="delivery_person")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    menu_items: Mapped[list["MenuItem"]] = relationship("MenuItem", back_populates="restaurant")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="menu_item")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="created")  # created/confirmed/preparing/out_for_delivery/delivered/cancelled
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    delivery_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="orders")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant", back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")
    delivery: Mapped[Optional["Delivery"]] = relationship("Delivery", back_populates="order", uselist=False, cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id", ondelete="RESTRICT"), nullable=False, index=True)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")  # stripe/mock/etc.
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")  # pending/authorized/captured/failed/refunded
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="payment")


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    delivery_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unassigned")  # unassigned/assigned/picked_up/in_transit/delivered/failed
    eta_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="delivery")
    delivery_person: Mapped[Optional["User"]] = relationship("User", back_populates="deliveries")
    status_history: Mapped[list["DeliveryStatusHistory"]] = relationship(
        "DeliveryStatusHistory", back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryStatusHistory(Base):
    __tablename__ = "delivery_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="status_history")
