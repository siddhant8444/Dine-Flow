import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False, index=True)
    suburb = Column(String, default="")
    currency = Column(String, default="AUD")
    gst_rate = Column(Float, default=10.0)
    abn = Column(String, default="")
    locale = Column(String, default="en")
    created_at = Column(DateTime, default=datetime.utcnow)

    tables = relationship("Table", back_populates="restaurant", cascade="all, delete")
    categories = relationship("MenuCategory", back_populates="restaurant", cascade="all, delete")


class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    table_number = Column(Integer, nullable=False)
    qr_token = Column(String, unique=True, default=lambda: str(uuid.uuid4()), index=True)
    is_occupied = Column(Boolean, default=False)

    restaurant = relationship("Restaurant", back_populates="tables")
    orders = relationship("Order", back_populates="table", cascade="all, delete")


class MenuCategory(Base):
    __tablename__ = "menu_categories"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name = Column(JSON, nullable=False)
    sort_order = Column(Integer, default=0)

    restaurant = relationship("Restaurant", back_populates="categories")
    items = relationship("MenuItem", back_populates="category", cascade="all, delete", order_by="MenuItem.sort_order")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("menu_categories.id"), nullable=False)
    name = Column(JSON, nullable=False)
    description = Column(JSON, default=dict)
    price = Column(Float, nullable=False)
    image_url = Column(String, default="")
    available = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    category = relationship("MenuCategory", back_populates="items")
    modifier_groups = relationship("ModifierGroup", back_populates="menu_item", cascade="all, delete")


class ModifierGroup(Base):
    __tablename__ = "modifier_groups"

    id = Column(Integer, primary_key=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name = Column(JSON, nullable=False)
    type = Column(String, default="single")
    is_required = Column(Boolean, default=False)

    menu_item = relationship("MenuItem", back_populates="modifier_groups")
    options = relationship("ModifierOption", back_populates="group", cascade="all, delete")


class ModifierOption(Base):
    __tablename__ = "modifier_options"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("modifier_groups.id"), nullable=False)
    name = Column(JSON, nullable=False)
    price_modifier = Column(Float, default=0.0)

    group = relationship("ModifierGroup", back_populates="options")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    status = Column(String, default="placed")
    created_at = Column(DateTime, default=datetime.utcnow)

    table = relationship("Table", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, default=1)
    notes = Column(String, default="")
    unit_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")
    modifiers = relationship("OrderItemModifier", back_populates="order_item", cascade="all, delete")


class OrderItemModifier(Base):
    __tablename__ = "order_item_modifiers"

    id = Column(Integer, primary_key=True, index=True)
    order_item_id = Column(Integer, ForeignKey("order_items.id"), nullable=False)
    name = Column(String, nullable=False)
    price_modifier = Column(Float, default=0.0)

    order_item = relationship("OrderItem", back_populates="modifiers")
