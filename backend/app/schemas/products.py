"""
schemas/products.py — Menu catalogue schemas
─────────────────────────────────────────────────────────────────────────────
Categories, menu items, variants, modifier groups and options.
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Modifier options
# ─────────────────────────────────────────────────────────────────────────────

class ModifierOptionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Extra cheese"])
    price_delta: Decimal = Field(default=Decimal("0.00"), description="Price adjustment, 0 = free")
    is_default: bool = False
    is_available: bool = True


class ModifierOptionUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    price_delta: Optional[Decimal] = None
    is_default: Optional[bool] = None
    is_available: Optional[bool] = None


class ModifierOptionRead(BaseModel):
    id: int
    name: str
    price_delta: Decimal
    is_default: bool
    is_available: bool
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Modifier groups
# ─────────────────────────────────────────────────────────────────────────────

class ModifierGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, examples=["Toppings"])
    required: bool = False
    min_selections: int = Field(default=0, ge=0)
    max_selections: int = Field(default=1, ge=1)
    display_order: int = Field(default=0, ge=0)
    options: list[ModifierOptionCreate] = Field(default_factory=list)


class ModifierGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    required: Optional[bool] = None
    min_selections: Optional[int] = Field(default=None, ge=0)
    max_selections: Optional[int] = Field(default=None, ge=1)
    display_order: Optional[int] = None


class ModifierGroupRead(BaseModel):
    id: int
    name: str
    required: bool
    min_selections: int
    max_selections: int
    display_order: int
    options: list[ModifierOptionRead] = []
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Variants
# ─────────────────────────────────────────────────────────────────────────────

class VariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Large"])
    sell_price: Decimal = Field(gt=0)
    cost_price: Optional[Decimal] = None
    barcode: Optional[str] = Field(default=None, max_length=100)
    sku: Optional[str] = Field(default=None, max_length=50)
    is_default: bool = False
    is_active: bool = True


class VariantRead(BaseModel):
    id: int
    name: str
    sell_price: Decimal
    cost_price: Optional[Decimal] = None
    barcode: Optional[str] = None
    sku: Optional[str] = None
    is_default: bool
    is_active: bool
    current_stock: Decimal
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Menu items
# ─────────────────────────────────────────────────────────────────────────────

class MenuItemCreate(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    image_url: Optional[str] = Field(default=None, max_length=500)
    sku: Optional[str] = Field(default=None, max_length=50)
    barcode: Optional[str] = Field(default=None, max_length=100)
    base_price: Decimal = Field(ge=0)
    cost_price: Optional[Decimal] = Field(default=None, ge=0)
    unit_of_measure_id: str = Field(default="piece")
    track_inventory: bool = False
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    kitchen_station_id: Optional[str] = None
    prep_time_minutes: int = Field(default=10, ge=0)
    is_available: bool = True
    variants: list[VariantCreate] = Field(default_factory=list)
    modifier_groups: list[ModifierGroupCreate] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_price: Optional[Decimal] = Field(default=None, ge=0)
    cost_price: Optional[Decimal] = None
    unit_of_measure_id: Optional[str] = None
    track_inventory: Optional[bool] = None
    low_stock_threshold: Optional[int] = None
    kitchen_station_id: Optional[str] = None
    prep_time_minutes: Optional[int] = None
    is_available: Optional[bool] = None
    variants: Optional[list[VariantCreate]] = None  # full replacement when provided


class MenuItemRead(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    barcode: Optional[str] = None
    base_price: Decimal
    cost_price: Optional[Decimal] = None
    unit_of_measure_id: str
    track_inventory: bool
    low_stock_threshold: Optional[int] = None
    current_stock: Decimal
    kitchen_station_id: Optional[str] = None
    prep_time_minutes: int
    is_available: bool
    variants: list[VariantRead] = []
    modifier_groups: list[ModifierGroupRead] = []
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Categories
# ─────────────────────────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    branch_id: Optional[int] = None
    parent_id: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=500)
    display_order: int = Field(default=0, ge=0)
    color_code: Optional[str] = Field(default=None, max_length=7)
    available_from: Optional[str] = Field(default=None, description="HH:MM — time-based availability start")
    available_until: Optional[str] = Field(default=None, description="HH:MM — time-based availability end")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    parent_id: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: Optional[int] = None
    color_code: Optional[str] = None
    available_from: Optional[str] = None
    available_until: Optional[str] = None
    is_active: Optional[bool] = None


class CategoryRead(BaseModel):
    id: int
    name: str
    branch_id: Optional[int] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    display_order: int
    is_active: bool
    color_code: Optional[str] = None
    available_from: Optional[str] = None
    available_until: Optional[str] = None
    items: list[MenuItemRead] = []
    children: list["CategoryRead"] = []
    model_config = {"from_attributes": True}


CategoryRead.model_rebuild()   # resolve forward reference


class CategoryReorderPayload(BaseModel):
    ordered_ids: list[int] = Field(min_length=1)
    parent_id: Optional[int] = None