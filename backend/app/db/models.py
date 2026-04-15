# ═══════════════════════════════════════════════════════════════════════════════
# models.py — Complete Restaurant POS System Data Layer
# ═══════════════════════════════════════════════════════════════════════════════
#
# Changes from v1:
#   IDENTITY
#   • StaffProfile: PIN fields (pin_hash, pin_fingerprint, pin_set_at,
#     pin_failed_attempts, pin_locked_until) + UniqueConstraint(branch_id,
#     pin_fingerprint) for branch-scoped PIN uniqueness.
#   • RefreshToken: first-class DB model for token rotation / revocation.
#
#   PRODUCT
#   • MenuItemStation: new association table enabling many-to-many item→station
#     routing (replaces single kitchen_station_id FK on MenuItem).
#   • MenuItem: keeps kitchen_station_id as "primary/default" station but gains
#     a `stations` M2M relationship for multi-station routing.
#
#   KITCHEN
#   • KdsTicket: now has UniqueConstraint(order_item_id, station_id) — one
#     ticket per item per station, not one ticket per item globally.
#   • KdsTicket.order_item back-populates to a LIST on PosOrderItem.
#
#   ORDERS
#   • PosOrderItem: removed kds_ticket_id single-FK; now has `kds_tickets`
#     one-to-many relationship (one item can produce tickets at multiple stations).
#
#   AUDIT & GOVERNANCE
#   • AuditLog: central, immutable log of privileged actions (void, discount,
#     cash-close, reprint, PIN reset).
#   • ManagerOverrideGrant: short-lived authorisation token for privileged
#     actions that require manager PIN approval.
#   • PrintJob: tracks PDF generation jobs (receipts, station tickets, Z-reports).
#
#   BUG FIXES
#   • DailySalesSummary.total_tax: fixed double-Mapped[Mapped[...]] type annotation.
#   • Branch: added `branch_settings` + `print_jobs` + `audit_logs` back-refs.
#   • VenueSettings.updated_at: default=func.now() added (was insert-only).
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any, List, Optional
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    declared_attr,
    declarative_base,
    mapped_column,
    relationship,
)
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class UserType(StrEnum):
    STAFF = "staff"
    CUSTOMER = "customer"


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    SERVER = "server"
    KITCHEN = "kitchen"
    KITCHEN_MANAGER = "kitchen_manager"


class StaffStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"


class TableStatus(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    CLEANING = "cleaning"


class PosOrderStatus(StrEnum):
    OPEN = "open"
    SENT = "sent"
    CLOSED = "closed"
    VOIDED = "voided"


class OrderType(StrEnum):
    DINE_IN = "dine_in"
    COUNTER = "counter"
    TAKEAWAY = "takeaway"
    ROOM_CHARGE = "room_charge"


class PaymentMethod(StrEnum):
    CASH = "cash"
    MOBILE_MONEY = "mobile_money"
    CARD = "card"
    ROOM_CHARGE = "room_charge"
    COMPLIMENTARY = "complimentary"


class CashSessionStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class StockMovementType(StrEnum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN_IN = "return_in"
    ADJUSTMENT = "adjustment"
    WASTE = "waste"
    TRANSFER = "transfer"


class DiscountType(StrEnum):
    PERCENT = "percent"
    FIXED = "fixed"


class KdsTicketStatus(StrEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class SystemTheme(StrEnum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    HIGH_CONTRAST = "high_contrast"


class ReceiptTemplate(StrEnum):
    STANDARD = "standard"
    COMPACT = "compact"
    DETAILED = "detailed"
    KITCHEN_TICKET = "kitchen_ticket"


class PrintJobType(StrEnum):
    RECEIPT = "receipt"
    STATION_TICKET = "station_ticket"
    Z_REPORT = "z_report"
    REPRINT = "reprint"


class PrintJobStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class OverrideAction(StrEnum):
    VOID_ITEM = "void_item"
    VOID_ORDER = "void_order"
    APPLY_DISCOUNT = "apply_discount"
    CASH_CLOSE = "cash_close"
    REPRINT = "reprint"
    PRICE_OVERRIDE = "price_override"


class AuditAction(StrEnum):
    # Identity
    STAFF_INVITED = "staff_invited"
    STAFF_ACTIVATED = "staff_activated"
    STAFF_DISABLED = "staff_disabled"
    PIN_SET = "pin_set"
    PIN_RESET = "pin_reset"
    PIN_LOCKED = "pin_locked"
    PIN_UNLOCKED = "pin_unlocked"
    # POS
    ORDER_VOIDED = "order_voided"
    ITEM_VOIDED = "item_voided"
    DISCOUNT_APPLIED = "discount_applied"
    PRICE_OVERRIDDEN = "price_overridden"
    CASH_SESSION_CLOSED = "cash_session_closed"
    PAID_OUT = "paid_out"
    SAFE_DROP = "safe_drop"
    # Printing
    RECEIPT_REPRINTED = "receipt_reprinted"


# ═══════════════════════════════════════════════════════════════════════════════
# MIXINS
# ═══════════════════════════════════════════════════════════════════════════════

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin:
    """Tracks the user who created/last updated a row.  Optional — nullable FKs."""

    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    @declared_attr
    def created_by(cls) -> Mapped[Optional["User"]]:
        return relationship("User", foreign_keys=f"[{cls.__name__}.created_by_id]")

    @declared_attr
    def updated_by(cls) -> Mapped[Optional["User"]]:
        return relationship("User", foreign_keys=f"[{cls.__name__}.updated_by_id]")


# ═══════════════════════════════════════════════════════════════════════════════
# IDENTITY & AUTH
# ═══════════════════════════════════════════════════════════════════════════════

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_type: Mapped[UserType] = mapped_column(SQLEnum(UserType))
    auth_provider: Mapped[AuthProvider] = mapped_column(SQLEnum(AuthProvider))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    staff_profile: Mapped[Optional["StaffProfile"]] = relationship(
        "StaffProfile", back_populates="user", uselist=False, lazy="joined"
    )
    customer_profile: Mapped[Optional["CustomerProfile"]] = relationship(
        "CustomerProfile", back_populates="user", uselist=False
    )
    kitchen_assignments: Mapped[List["KitchenStaffAssignment"]] = relationship(
        "KitchenStaffAssignment", back_populates="staff"
    )
    orders: Mapped[List["PosOrder"]] = relationship("PosOrder", back_populates="staff_user")
    cash_sessions: Mapped[List["CashSession"]] = relationship(
        "CashSession", back_populates="staff_user"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class StaffProfile(Base):
    """
    One-to-one extension of User for staff-specific data.

    PIN strategy (blueprint §5):
      pin_hash        — bcrypt hash for verification
      pin_fingerprint — deterministic HMAC digest; UNIQUE per branch for fast
                        collision detection without reversing the hash
    """

    __tablename__ = "staff_profiles"
    __table_args__ = (
        # Enforce PIN uniqueness per branch without exposing the raw PIN.
        # Partial index: only non-NULL fingerprints participate.
        Index(
            "uq_staff_pin_fingerprint_per_branch",
            "branch_id",
            "pin_fingerprint",
            unique=True,
            postgresql_where=sa.text("pin_fingerprint IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    role: Mapped[Role] = mapped_column(SQLEnum(Role))
    status: Mapped[StaffStatus] = mapped_column(
        SQLEnum(StaffStatus), default=StaffStatus.INVITED
    )
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── PIN fields (blueprint §5.1) ───────────────────────────────────────────
    pin_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # HMAC-SHA256 hex digest used for unique-per-branch indexing
    pin_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pin_set_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Failed PIN attempt counter (reset on success, lock at threshold)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pin_locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="staff_profile", foreign_keys=[user_id]
    )
    branch: Mapped[Optional["Branch"]] = relationship("Branch", foreign_keys=[branch_id])


class CustomerProfile(Base, TimestampMixin):
    __tablename__ = "customer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    google_subject: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="customer_profile")


class RefreshToken(Base):
    """
    Stored refresh tokens enable revocation (logout from all devices, stolen
    token invalidation).  One user may hold multiple active tokens
    (multiple devices / POS terminals).

    On login: create a new RefreshToken row, return the raw token to the client.
    On refresh: look up by token_hash, verify not revoked / expired, issue new.
    On logout:  set revoked_at.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # SHA-256 hex of the raw token — fast lookup, no bcrypt overhead
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Informational — helps audit which device the session belongs to
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.now(UTC)


# ═══════════════════════════════════════════════════════════════════════════════
# VENUE & BRANCH
# ═══════════════════════════════════════════════════════════════════════════════

class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(20), unique=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Nairobi")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    tables: Mapped[List["Table"]] = relationship("Table", back_populates="branch")
    menu_categories: Mapped[List["MenuCategory"]] = relationship(
        "MenuCategory", back_populates="branch"
    )
    tax_configs: Mapped[List["TaxConfig"]] = relationship(
        "TaxConfig", back_populates="branch"
    )
    orders: Mapped[List["PosOrder"]] = relationship("PosOrder", back_populates="branch")
    stock_movements: Mapped[List["StockMovement"]] = relationship(
        "StockMovement", back_populates="branch"
    )
    cash_sessions: Mapped[List["CashSession"]] = relationship(
        "CashSession", back_populates="branch"
    )
    branch_settings: Mapped[Optional["BranchSettings"]] = relationship(
        "BranchSettings", back_populates="branch", uselist=False
    )
    print_jobs: Mapped[List["PrintJob"]] = relationship(
        "PrintJob", back_populates="branch"
    )


class VenueSettings(Base):
    """Singleton row — one per deployment.  id is always 'default'."""

    __tablename__ = "venue_settings"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="default")

    # Identity
    restaurant_name: Mapped[str] = mapped_column(String(255), default="RestaurantOS")
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Branding
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    receipt_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#10B981")

    # Locale
    currency: Mapped[str] = mapped_column(String(10), default="KES")
    currency_symbol: Mapped[str] = mapped_column(String(10), default="KSh")
    timezone: Mapped[str] = mapped_column(String(64), default="Africa/Nairobi")
    date_format: Mapped[str] = mapped_column(String(20), default="DD/MM/YYYY")
    time_format: Mapped[str] = mapped_column(String(10), default="24h")

    # Tax
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("16.00"))
    tax_inclusive: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_label: Mapped[str] = mapped_column(String(20), default="VAT")
    secondary_tax_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    secondary_tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("2.00")
    )
    secondary_tax_label: Mapped[str] = mapped_column(String(20), default="Service Charge")

    # Receipt
    receipt_footer: Mapped[str] = mapped_column(
        String(500), default="Thank you for dining with us!"
    )
    receipt_show_vat_breakdown: Mapped[bool] = mapped_column(Boolean, default=True)
    receipt_show_staff_name: Mapped[bool] = mapped_column(Boolean, default=True)
    receipt_template: Mapped[ReceiptTemplate] = mapped_column(
        SQLEnum(ReceiptTemplate), default=ReceiptTemplate.STANDARD
    )

    # System behaviour
    theme: Mapped[SystemTheme] = mapped_column(
        SQLEnum(SystemTheme), default=SystemTheme.SYSTEM
    )
    auto_logout_minutes: Mapped[int] = mapped_column(Integer, default=30)
    require_void_reason: Mapped[bool] = mapped_column(Boolean, default=True)
    require_discount_auth: Mapped[bool] = mapped_column(Boolean, default=True)
    min_discount_auth_role: Mapped[Role] = mapped_column(
        SQLEnum(Role), default=Role.MANAGER
    )

    # PIN lockout policy
    pin_max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    pin_lockout_minutes: Mapped[int] = mapped_column(Integer, default=5)

    # Feature flags
    enable_kds: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_loyalty: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_reservations: Mapped[bool] = mapped_column(Boolean, default=False)
    enable_customer_display: Mapped[bool] = mapped_column(Boolean, default=False)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Bug fix: was missing server_default so the column had no value on INSERT
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class BranchSettings(Base):
    """Per-branch overrides applied on top of VenueSettings."""

    __tablename__ = "branch_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"), unique=True)

    receipt_footer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    printer_kitchen_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    printer_receipt_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    kds_display_mode: Mapped[str] = mapped_column(String(20), default="grid")

    branch: Mapped["Branch"] = relationship("Branch", back_populates="branch_settings")


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT CONFIGURATION (catalogue prerequisites)
# ═══════════════════════════════════════════════════════════════════════════════

class UnitOfMeasure(Base, TimestampMixin):
    __tablename__ = "units_of_measure"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(20), default="discrete")  # discrete|weight|volume
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class KitchenStation(Base, TimestampMixin):
    """Production station (bar / grill / fryer / dessert …)."""

    __tablename__ = "kitchen_stations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    print_order: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    assigned_staff: Mapped[List["KitchenStaffAssignment"]] = relationship(
        "KitchenStaffAssignment", back_populates="station"
    )
    # Many-to-many back-ref to menu items
    menu_items: Mapped[List["MenuItem"]] = relationship(
        "MenuItem",
        secondary="menu_item_stations",
        back_populates="stations",
    )
    kds_tickets: Mapped[List["KdsTicket"]] = relationship(
        "KdsTicket", back_populates="station"
    )


class InventoryPolicy(Base):
    """Singleton inventory configuration — id is always 'default'."""

    __tablename__ = "inventory_policy"

    id: Mapped[str] = mapped_column(String(50), primary_key=True, default="default")
    default_track_inventory: Mapped[bool] = mapped_column(Boolean, default=False)
    default_low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10)
    enable_auto_depletion: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_waste_logging: Mapped[bool] = mapped_column(Boolean, default=True)
    default_costing_method: Mapped[str] = mapped_column(
        String(20), default="average"
    )  # fifo | average | latest
    enable_stock_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_recipients: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True
    )  # JSON array of emails
    updated_at: Mapped[str] = mapped_column(String(50))  # ISO timestamp


class TaxTemplate(Base, TimestampMixin):
    """Reusable tax rules that can be assigned to categories or items."""

    __tablename__ = "tax_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100))
    rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    is_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    applies_to: Mapped[str] = mapped_column(String(20), default="all")  # all|categories|items
    target_ids: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True
    )  # JSON array
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT & MENU
# ═══════════════════════════════════════════════════════════════════════════════

class MenuCategory(Base, TimestampMixin):
    __tablename__ = "menu_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.id"), nullable=True
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    available_from: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    available_until: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    color_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)

    branch: Mapped[Optional["Branch"]] = relationship(
        "Branch", back_populates="menu_categories"
    )
    parent: Mapped[Optional["MenuCategory"]] = relationship(
        "MenuCategory", remote_side="MenuCategory.id", back_populates="children"
    )
    children: Mapped[List["MenuCategory"]] = relationship(
        "MenuCategory",
        back_populates="parent",
        cascade="all, delete-orphan",
        order_by="MenuCategory.display_order, MenuCategory.name",
    )
    items: Mapped[List["MenuItem"]] = relationship(
        "MenuItem", back_populates="category", order_by="MenuItem.name"
    )


# ── Many-to-many: MenuItem ↔ KitchenStation ───────────────────────────────────
# Replaces the old single-FK approach.  One item can now route to multiple
# production stations (e.g. a Surf & Turf routes to both Grill and Fryer).
menu_item_stations = Table(
    "menu_item_stations",
    Base.metadata,
    Column(
        "menu_item_id",
        Integer,
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "station_id",
        String(50),
        ForeignKey("kitchen_stations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    UniqueConstraint("menu_item_id", "station_id", name="uq_menu_item_station"),
)


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id"))

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)

    # Pricing
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    # Inventory
    unit_of_measure_id: Mapped[str] = mapped_column(
        ForeignKey("units_of_measure.id"), default="piece"
    )
    track_inventory: Mapped[bool] = mapped_column(Boolean, default=False)
    low_stock_threshold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))

    # Kitchen — kept as optional "primary station" convenience FK;
    # full multi-station routing lives in the menu_item_stations M2M table
    kitchen_station_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("kitchen_stations.id"), nullable=True
    )
    prep_time_minutes: Mapped[int] = mapped_column(Integer, default=10)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    category: Mapped["MenuCategory"] = relationship("MenuCategory", back_populates="items")
    unit_of_measure: Mapped["UnitOfMeasure"] = relationship("UnitOfMeasure")
    # Multi-station M2M
    stations: Mapped[List["KitchenStation"]] = relationship(
        "KitchenStation",
        secondary="menu_item_stations",
        back_populates="menu_items",
    )
    variants: Mapped[List["MenuItemVariant"]] = relationship(
        "MenuItemVariant", back_populates="menu_item", cascade="all, delete-orphan"
    )
    modifier_groups: Mapped[List["MenuModifierGroup"]] = relationship(
        "MenuModifierGroup", back_populates="menu_item", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[List["StockMovement"]] = relationship(
        "StockMovement", back_populates="menu_item"
    )
    kds_tickets: Mapped[List["KdsTicket"]] = relationship(
        "KdsTicket", back_populates="menu_item"
    )


class MenuItemVariant(Base, TimestampMixin):
    """Size / portion variants: Large, Medium, Small…"""

    __tablename__ = "menu_item_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    sell_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))

    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="variants")
    stock_movements: Mapped[List["StockMovement"]] = relationship(
        "StockMovement", back_populates="variant"
    )
    order_items: Mapped[List["PosOrderItem"]] = relationship(
        "PosOrderItem", back_populates="variant"
    )


class MenuModifierGroup(Base, TimestampMixin):
    __tablename__ = "menu_modifier_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    min_selections: Mapped[int] = mapped_column(Integer, default=0)
    max_selections: Mapped[int] = mapped_column(Integer, default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    menu_item: Mapped["MenuItem"] = relationship(
        "MenuItem", back_populates="modifier_groups"
    )
    options: Mapped[List["MenuModifierOption"]] = relationship(
        "MenuModifierOption", back_populates="group", cascade="all, delete-orphan"
    )


class MenuModifierOption(Base, TimestampMixin):
    __tablename__ = "menu_modifier_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("menu_modifier_groups.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(120))
    price_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    group: Mapped["MenuModifierGroup"] = relationship(
        "MenuModifierGroup", back_populates="options"
    )
    order_item_modifiers: Mapped[List["PosOrderItemModifier"]] = relationship(
        "PosOrderItemModifier", back_populates="option"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# KITCHEN DISPLAY SYSTEM (KDS)
# ═══════════════════════════════════════════════════════════════════════════════

class KitchenStaffAssignment(Base, TimestampMixin):
    """Links staff to stations (many-to-many with metadata)."""

    __tablename__ = "kitchen_staff_assignments"
    __table_args__ = (
        UniqueConstraint(
            "staff_user_id", "station_id", name="uq_kitchen_assignment"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    station_id: Mapped[str] = mapped_column(ForeignKey("kitchen_stations.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True)
    can_bump: Mapped[bool] = mapped_column(Boolean, default=True)

    staff: Mapped["User"] = relationship("User", back_populates="kitchen_assignments")
    station: Mapped["KitchenStation"] = relationship(
        "KitchenStation", back_populates="assigned_staff"
    )


class KdsTicket(Base, TimestampMixin):
    """
    One ticket per (order_item, station) — enforced by UniqueConstraint.

    When an order item routes to N stations (via the M2M table), N KdsTickets
    are created, one per station.  Each has an independent status lifecycle.
    """

    __tablename__ = "kds_tickets"
    __table_args__ = (
        # Blueprint §6.2: "unique (order_item_id, station_id)"
        UniqueConstraint("order_item_id", "station_id", name="uq_kds_ticket_item_station"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("pos_orders.id"))
    order_item_id: Mapped[int] = mapped_column(ForeignKey("pos_order_items.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    station_id: Mapped[str] = mapped_column(ForeignKey("kitchen_stations.id"))

    # Denormalised snapshot for KDS display (avoids JOINs on the hot path)
    item_name: Mapped[str] = mapped_column(String(200))
    quantity: Mapped[int] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    modifiers_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle
    status: Mapped[KdsTicketStatus] = mapped_column(
        SQLEnum(KdsTicketStatus), default=KdsTicketStatus.PENDING
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)  # 0=normal 1=rush 2=vip
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ready_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    served_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_prep_time: Mapped[int] = mapped_column(Integer, default=10)

    order: Mapped["PosOrder"] = relationship("PosOrder", back_populates="kds_tickets")
    # back_populates to LIST on PosOrderItem (was Optional in v1)
    order_item: Mapped["PosOrderItem"] = relationship(
        "PosOrderItem", back_populates="kds_tickets"
    )
    menu_item: Mapped["MenuItem"] = relationship(
        "MenuItem", back_populates="kds_tickets"
    )
    station: Mapped["KitchenStation"] = relationship(
        "KitchenStation", back_populates="kds_tickets"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TABLES & RESERVATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class Table(Base, TimestampMixin):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    table_number: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    status: Mapped[TableStatus] = mapped_column(
        SQLEnum(TableStatus), default=TableStatus.AVAILABLE
    )
    qr_code_token: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: str(uuid.uuid4())
    )
    position_x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    position_y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floor_zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="tables")
    orders: Mapped[List["PosOrder"]] = relationship("PosOrder", back_populates="table")
    reservations: Mapped[List["TableReservation"]] = relationship(
        "TableReservation", back_populates="table"
    )


class TableReservation(Base, TimestampMixin):
    __tablename__ = "table_reservations"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_id: Mapped[int] = mapped_column(ForeignKey("tables.id"))
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    party_size: Mapped[int] = mapped_column(Integer)
    reservation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=120)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    special_requests: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    table: Mapped["Table"] = relationship("Table", back_populates="reservations")


# ═══════════════════════════════════════════════════════════════════════════════
# ORDERS & PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════

class PosOrder(Base, TimestampMixin):
    __tablename__ = "pos_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    table_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tables.id"), nullable=True
    )
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    order_type: Mapped[OrderType] = mapped_column(
        SQLEnum(OrderType), default=OrderType.DINE_IN
    )
    status: Mapped[PosOrderStatus] = mapped_column(
        SQLEnum(PosOrderStatus), default=PosOrderStatus.OPEN
    )

    room_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Financials
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )

    # Legacy / convenience payment columns (full split detail in PosPayment)
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        SQLEnum(PaymentMethod), nullable=True
    )
    amount_paid: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    change_due: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch", back_populates="orders")
    table: Mapped[Optional["Table"]] = relationship("Table", back_populates="orders")
    staff_user: Mapped["User"] = relationship("User", back_populates="orders")
    items: Mapped[List["PosOrderItem"]] = relationship(
        "PosOrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[List["PosPayment"]] = relationship(
        "PosPayment", back_populates="order", cascade="all, delete-orphan"
    )
    discounts: Mapped[List["OrderDiscount"]] = relationship(
        "OrderDiscount", back_populates="order", cascade="all, delete-orphan"
    )
    kds_tickets: Mapped[List["KdsTicket"]] = relationship(
        "KdsTicket", back_populates="order"
    )
    print_jobs: Mapped[List["PrintJob"]] = relationship(
        "PrintJob", back_populates="order"
    )


class PosOrderItem(Base, TimestampMixin):
    __tablename__ = "pos_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pos_orders.id", ondelete="CASCADE")
    )
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    variant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_item_variants.id"), nullable=True
    )

    # Snapshots — denormalised for historical accuracy after menu changes
    menu_item_name: Mapped[str] = mapped_column(String(200))
    variant_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_voided: Mapped[bool] = mapped_column(Boolean, default=False)
    void_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    voided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    voided_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    sent_to_kitchen: Mapped[bool] = mapped_column(Boolean, default=False)

    order: Mapped["PosOrder"] = relationship("PosOrder", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")
    variant: Mapped[Optional["MenuItemVariant"]] = relationship(
        "MenuItemVariant", back_populates="order_items"
    )
    modifiers: Mapped[List["PosOrderItemModifier"]] = relationship(
        "PosOrderItemModifier", back_populates="order_item", cascade="all, delete-orphan"
    )
    # One-to-MANY: one item can produce tickets at multiple stations
    kds_tickets: Mapped[List["KdsTicket"]] = relationship(
        "KdsTicket", back_populates="order_item"
    )
    voided_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[voided_by_id]
    )


class PosOrderItemModifier(Base, TimestampMixin):
    __tablename__ = "pos_order_item_modifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("pos_order_items.id", ondelete="CASCADE")
    )
    option_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_modifier_options.id"), nullable=True
    )
    option_name: Mapped[str] = mapped_column(String(120))
    price_delta: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    order_item: Mapped["PosOrderItem"] = relationship(
        "PosOrderItem", back_populates="modifiers"
    )
    option: Mapped[Optional["MenuModifierOption"]] = relationship("MenuModifierOption")


class OrderDiscount(Base, TimestampMixin):
    __tablename__ = "order_discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pos_orders.id", ondelete="CASCADE")
    )
    order_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pos_order_items.id", ondelete="CASCADE"), nullable=True
    )

    discount_type: Mapped[DiscountType] = mapped_column(SQLEnum(DiscountType))
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    authorized_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    order: Mapped["PosOrder"] = relationship("PosOrder", back_populates="discounts")
    order_item: Mapped[Optional["PosOrderItem"]] = relationship("PosOrderItem")
    authorized_by: Mapped[Optional["User"]] = relationship("User")


class PosPayment(Base, TimestampMixin):
    __tablename__ = "pos_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("pos_orders.id", ondelete="CASCADE")
    )
    method: Mapped[PaymentMethod] = mapped_column(SQLEnum(PaymentMethod))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reference: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True
    )  # gateway transaction ID / M-Pesa code
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    order: Mapped["PosOrder"] = relationship("PosOrder", back_populates="payments")


# ═══════════════════════════════════════════════════════════════════════════════
# INVENTORY & STOCK
# ═══════════════════════════════════════════════════════════════════════════════

class StockMovement(Base, TimestampMixin, AuditMixin):
    """Immutable ledger — never update or delete rows, only insert."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    variant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_item_variants.id"), nullable=True
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))  # positive=in, negative=out
    movement_type: Mapped[StockMovementType] = mapped_column(SQLEnum(StockMovementType))
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)

    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    branch: Mapped["Branch"] = relationship("Branch", back_populates="stock_movements")
    menu_item: Mapped["MenuItem"] = relationship(
        "MenuItem", back_populates="stock_movements"
    )
    variant: Mapped[Optional["MenuItemVariant"]] = relationship(
        "MenuItemVariant", back_populates="stock_movements"
    )


class StockAdjustment(Base, TimestampMixin, AuditMixin):
    __tablename__ = "stock_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    variant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_item_variants.id"), nullable=True
    )

    quantity_before: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    reason: Mapped[str] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CASH MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class CashSession(Base, TimestampMixin):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opening_float: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    closing_float: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    expected_closing: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    status: Mapped[CashSessionStatus] = mapped_column(
        SQLEnum(CashSessionStatus), default=CashSessionStatus.OPEN
    )

    total_cash_sales: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    total_card_sales: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    total_mobile_sales: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    discrepancy: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    closure_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    branch: Mapped["Branch"] = relationship("Branch", back_populates="cash_sessions")
    staff_user: Mapped["User"] = relationship("User", back_populates="cash_sessions")


class CashTransaction(Base, TimestampMixin):
    """Petty cash, paid outs, safe drops within a session."""

    __tablename__ = "cash_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("cash_sessions.id"))
    transaction_type: Mapped[str] = mapped_column(String(20))  # paid_out|safe_drop|refund
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(String(255))
    authorized_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


# ═══════════════════════════════════════════════════════════════════════════════
# TAX CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class TaxConfig(Base, TimestampMixin):
    __tablename__ = "tax_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.id"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(80), default="VAT")
    rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.1600"))
    is_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)

    branch: Mapped[Optional["Branch"]] = relationship(
        "Branch", back_populates="tax_configs"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PRINTING
# ═══════════════════════════════════════════════════════════════════════════════

class PrintJob(Base, TimestampMixin):
    """
    Ledger of all print requests.  MVP = PDF generation; later = ESC/POS
    printer routing.  Keeping the ledger from day one enables reprints,
    auditing, and future printer-management without schema changes.
    """

    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pos_orders.id"), nullable=True
    )
    station_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("kitchen_stations.id"), nullable=True
    )
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    job_type: Mapped[PrintJobType] = mapped_column(SQLEnum(PrintJobType))
    status: Mapped[PrintJobStatus] = mapped_column(
        SQLEnum(PrintJobStatus), default=PrintJobStatus.PENDING
    )

    # Snapshot of printable data at the moment of request
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # URL / path to the generated PDF (populated on completion)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    branch: Mapped["Branch"] = relationship("Branch", back_populates="print_jobs")
    order: Mapped[Optional["PosOrder"]] = relationship(
        "PosOrder", back_populates="print_jobs"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIT & GOVERNANCE
# ═══════════════════════════════════════════════════════════════════════════════

class AuditLog(Base):
    """
    Central, append-only log of all privileged actions.

    Every void, discount, price override, PIN reset, cash-close discrepancy
    acceptance, and reprint writes a row here with a full payload snapshot
    so the record is self-contained even if the underlying data changes.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("branches.id"), nullable=True
    )
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )  # Manager who authorised via PIN/password

    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    payload: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Before/after state snapshot

    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id])
    approved_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[approved_by_id]
    )


class ManagerOverrideGrant(Base):
    """
    Short-lived, single-use authorisation granted by a manager (via PIN) for
    one privileged action (void / discount / cash-close / reprint).

    Flow:
      1. Cashier requests action → system prompts for manager PIN
      2. Manager enters PIN → ManagerOverrideGrant row created (TTL = 2 min)
      3. Cashier performs action → grant is consumed (used_at set)
      4. AuditLog row written referencing both actor and approved_by
    """

    __tablename__ = "manager_override_grants"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    action: Mapped[OverrideAction] = mapped_column(SQLEnum(OverrideAction))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    granted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    granted_by: Mapped["User"] = relationship("User", foreign_keys=[granted_by_id])
    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id])

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > datetime.now(UTC)


# ═══════════════════════════════════════════════════════════════════════════════
# REPORTING VIEWS (Materialised — managed outside ORM via Alembic raw DDL)
# ═══════════════════════════════════════════════════════════════════════════════

class DailySalesSummary(Base):
    """
    PostgreSQL materialised view — refreshed by a cron job / background task.
    The ORM mapping is READ-ONLY; never write to this table via SQLAlchemy.
    """

    __tablename__ = "mv_daily_sales_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    total_orders: Mapped[int] = mapped_column(Integer)
    total_sales: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_discounts: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2))  # BUG FIX: was Mapped[Mapped[...]]
    avg_order_value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    void_count: Mapped[int] = mapped_column(Integer)
    void_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class InventorySnapshot(Base):
    """READ-ONLY materialised view — current stock levels by branch."""

    __tablename__ = "mv_inventory_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id"))
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    variant_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("menu_item_variants.id"), nullable=True
    )
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    last_movement_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)