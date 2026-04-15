"""
schemas/settings_product.py — Catalogue configuration schemas
─────────────────────────────────────────────────────────────────────────────
Units of measure, kitchen stations, inventory policy, tax templates.
These are the prerequisites that must exist before any MenuItem can be created.
"""

import json
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Units of measure
# ─────────────────────────────────────────────────────────────────────────────

class UnitOfMeasureCreate(BaseModel):
    id: str = Field(min_length=1, max_length=50, examples=["piece"])
    name: str = Field(min_length=1, max_length=100, examples=["Piece"])
    category: str = Field(default="discrete")   # discrete | weight | volume
    description: Optional[str] = Field(default=None, max_length=500)
    sort_order: int = Field(default=0, ge=0)


class UnitOfMeasureUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    category: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=500)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class UnitOfMeasureResponse(BaseModel):
    id: str
    name: str
    category: str
    description: Optional[str] = None
    sort_order: int
    is_active: bool
    model_config = {"from_attributes": True}


class UnitReorderPayload(BaseModel):
    ordered_ids: list[str] = Field(min_length=1)


# ─────────────────────────────────────────────────────────────────────────────
# Kitchen stations
# ─────────────────────────────────────────────────────────────────────────────

class KitchenStationCreate(BaseModel):
    id: str = Field(min_length=1, max_length=50, examples=["grill"])
    name: str = Field(min_length=1, max_length=100, examples=["Grill Station"])
    color: str = Field(default="#3B82F6", max_length=7)
    print_order: int = Field(default=1, ge=1)
    description: Optional[str] = Field(default=None, max_length=500)


class KitchenStationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    color: Optional[str] = Field(default=None, max_length=7)
    print_order: Optional[int] = Field(default=None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class KitchenStationResponse(BaseModel):
    id: str
    name: str
    color: str
    print_order: int
    is_active: bool
    description: Optional[str] = None
    model_config = {"from_attributes": True}


class StationReorderPayload(BaseModel):
    ordered_ids: list[str] = Field(min_length=1)


# ─────────────────────────────────────────────────────────────────────────────
# Inventory policy  (singleton)
# ─────────────────────────────────────────────────────────────────────────────

class InventoryPolicyUpdate(BaseModel):
    default_track_inventory: Optional[bool] = None
    default_low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    enable_auto_depletion: Optional[bool] = None
    enable_waste_logging: Optional[bool] = None
    default_costing_method: Optional[str] = None   # fifo | average | latest
    enable_stock_alerts: Optional[bool] = None
    alert_recipients: Optional[list[str]] = None


class InventoryPolicyResponse(BaseModel):
    id: str
    default_track_inventory: bool
    default_low_stock_threshold: int
    enable_auto_depletion: bool
    enable_waste_logging: bool
    default_costing_method: str
    enable_stock_alerts: bool
    alert_recipients: list[str] = []
    updated_at: str
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Tax templates
# ─────────────────────────────────────────────────────────────────────────────

class TaxTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Standard VAT 16%"])
    rate: Decimal = Field(gt=0, le=1, description="Decimal fraction e.g. 0.16 = 16%")
    is_inclusive: bool = False
    is_default: bool = False
    applies_to: str = Field(default="all")   # all | categories | items
    target_ids: Optional[list[str]] = None
    is_active: bool = True


class TaxTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    rate: Optional[Decimal] = Field(default=None, gt=0, le=1)
    is_inclusive: Optional[bool] = None
    is_default: Optional[bool] = None
    applies_to: Optional[str] = None
    target_ids: Optional[list[str]] = None
    is_active: Optional[bool] = None


class TaxTemplateResponse(BaseModel):
    id: str
    name: str
    rate: Decimal
    is_inclusive: bool
    is_default: bool
    applies_to: str
    target_ids: list[str] = []
    is_active: bool
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Bulk configuration response  (GET /settings/product/configuration)
# ─────────────────────────────────────────────────────────────────────────────

class ProductConfigurationResponse(BaseModel):
    units: list[UnitOfMeasureResponse]
    stations: list[KitchenStationResponse]
    inventory_policy: InventoryPolicyResponse
    tax_templates: list[TaxTemplateResponse]


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper  (used in route layer to deserialise JSON-string fields)
# ─────────────────────────────────────────────────────────────────────────────

def deserialize_json_list(value: Optional[str]) -> list:
    """Parse a JSON-encoded list stored as a string column, returning [] on failure."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []