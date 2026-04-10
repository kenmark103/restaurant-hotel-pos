from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KitchenStation


class VariantCreate(BaseModel):
    name: str = Field(..., max_length=100)
    sell_price: Decimal = Field(..., ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, max_length=50)
    display_order: int = 0
    is_default: bool = False


class VariantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    sell_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    barcode: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, max_length=50)
    display_order: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None


class VariantRead(BaseModel):
    id: int
    menu_item_id: int
    name: str
    sell_price: Decimal
    cost_price: Decimal | None
    barcode: str | None
    sku: str | None
    display_order: int
    is_default: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    branch_id: int | None = None
    parent_id: int | None = None
    name: str = Field(..., max_length=100)
    description: str | None = Field(default=None, max_length=500)
    display_order: int = 0
    available_from: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    available_until: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


class MenuItemCreate(BaseModel):
    category_id: int
    name: str = Field(..., max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    sku: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=100)
    base_price: Decimal = Field(..., ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    unit_of_measure: str = Field(default="piece", max_length=30)
    track_inventory: bool = False
    low_stock_threshold: int | None = Field(default=None, ge=0)
    prep_time_minutes: int = Field(default=10, ge=0, le=300)
    station: KitchenStation = KitchenStation.ANY
    is_available: bool = True
    variants: list[VariantCreate] = Field(default_factory=list)


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=500)
    sku: str | None = Field(default=None, max_length=50)
    barcode: str | None = Field(default=None, max_length=100)
    base_price: Decimal | None = Field(default=None, ge=0)
    cost_price: Decimal | None = Field(default=None, ge=0)
    unit_of_measure: str | None = Field(default=None, max_length=30)
    track_inventory: bool | None = None
    low_stock_threshold: int | None = Field(default=None, ge=0)
    prep_time_minutes: int | None = Field(default=None, ge=0, le=300)
    station: KitchenStation | None = None
    is_available: bool | None = None


class MenuItemRead(BaseModel):
    id: int
    category_id: int
    name: str
    description: str | None
    image_url: str | None
    sku: str | None
    barcode: str | None
    base_price: Decimal
    cost_price: Decimal | None
    unit_of_measure: str
    track_inventory: bool
    low_stock_threshold: int | None
    prep_time_minutes: int
    station: KitchenStation
    is_available: bool
    variants: list[VariantRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MenuCategoryRead(BaseModel):
    id: int
    branch_id: int | None
    parent_id: int | None
    name: str
    description: str | None
    display_order: int
    is_active: bool
    available_from: str | None
    available_until: str | None
    children: list["MenuCategoryRead"] = Field(default_factory=list)
    items: list[MenuItemRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StockLevelRead(BaseModel):
    menu_item_id: int
    variant_id: int | None
    name: str
    variant_name: str | None
    current_stock: Decimal
    unit_of_measure: str
    low_stock_threshold: int | None
    is_low: bool


CategoryRead = MenuCategoryRead
MenuCategoryRead.model_rebuild()
