from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class _BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# -------------------------
# Users
# -------------------------
class UserCreate(_BaseSchema):
    email: EmailStr = Field(..., description="User email (unique).")
    name: str = Field(..., min_length=1, max_length=255, description="Display name.")
    role: str = Field("customer", description="Role: customer/admin/delivery.")
    password: Optional[str] = Field(None, description="Plain password (will be hashed by future auth layer).")


class UserRead(_BaseSchema):
    id: int
    email: EmailStr
    name: str
    role: str
    created_at: datetime


# -------------------------
# Restaurants
# -------------------------
class RestaurantCreate(_BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    address: Optional[str] = Field(None, max_length=500)


class RestaurantRead(_BaseSchema):
    id: int
    name: str
    description: Optional[str]
    address: Optional[str]
    created_at: datetime


# -------------------------
# Menu items
# -------------------------
class MenuItemCreate(_BaseSchema):
    restaurant_id: int
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Decimal = Field(..., description="Item price.")
    image_url: Optional[str] = Field(None, max_length=500)
    is_available: bool = True


class MenuItemRead(_BaseSchema):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str]
    price: Decimal
    image_url: Optional[str]
    is_available: bool
    created_at: datetime


# -------------------------
# Orders
# -------------------------
class OrderItemCreate(_BaseSchema):
    menu_item_id: int
    quantity: int = Field(1, ge=1)


class OrderCreate(_BaseSchema):
    user_id: int
    restaurant_id: int
    delivery_address: Optional[str] = Field(None, max_length=500)
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderItemRead(_BaseSchema):
    id: int
    order_id: int
    menu_item_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderRead(_BaseSchema):
    id: int
    user_id: int
    restaurant_id: int
    status: str
    total_amount: Decimal
    delivery_address: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = []


# -------------------------
# Payments
# -------------------------
class PaymentCreate(_BaseSchema):
    order_id: int
    provider: str = Field("mock", max_length=100)
    amount: Decimal
    provider_payment_id: Optional[str] = Field(None, max_length=255)
    raw_payload: Optional[str] = None


class PaymentRead(_BaseSchema):
    id: int
    order_id: int
    provider: str
    status: str
    amount: Decimal
    provider_payment_id: Optional[str]
    raw_payload: Optional[str]
    created_at: datetime
    updated_at: datetime


# -------------------------
# Deliveries
# -------------------------
class DeliveryCreate(_BaseSchema):
    order_id: int
    delivery_person_id: Optional[int] = None
    eta_minutes: Optional[int] = Field(None, ge=1)


class DeliveryRead(_BaseSchema):
    id: int
    order_id: int
    delivery_person_id: Optional[int]
    status: str
    eta_minutes: Optional[int]
    created_at: datetime
    updated_at: datetime


class DeliveryStatusHistoryCreate(_BaseSchema):
    delivery_id: int
    status: str = Field(..., max_length=50)
    note: Optional[str] = None


class DeliveryStatusHistoryRead(_BaseSchema):
    id: int
    delivery_id: int
    status: str
    note: Optional[str]
    created_at: datetime
