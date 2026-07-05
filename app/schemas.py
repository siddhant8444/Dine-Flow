from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ModifierOptionCreate(BaseModel):
    name: dict
    price_modifier: float = 0.0


class ModifierGroupCreate(BaseModel):
    name: dict
    type: str = "single"
    is_required: bool = False
    options: List[ModifierOptionCreate] = []


class MenuItemCreate(BaseModel):
    name: dict
    description: Optional[dict] = None
    price: float
    image_url: str = ""
    available: bool = True
    sort_order: int = 0
    modifier_groups: List[ModifierGroupCreate] = []


class CategoryCreate(BaseModel):
    name: dict
    sort_order: int = 0
    items: List[MenuItemCreate] = []


class OrderItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = 1
    notes: str = ""
    modifier_ids: List[int] = []


class PlaceOrderRequest(BaseModel):
    table_token: str
    items: List[OrderItemRequest]


class OrderStatusUpdate(BaseModel):
    status: str
