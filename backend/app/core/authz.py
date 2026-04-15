"""
authz.py — RBAC policy map + branch-scope helpers
─────────────────────────────────────────────────────────────────────────────
Centralises all "who can do what" logic so it's never scattered across
route files.  Services that need branch-scope checks call the helpers here
rather than reimplementing inline.

Usage:
    from app.core.authz import can, require_capability, ROLE_CAPABILITIES

    # In a service method:
    if not can(user, Capability.VOID_ORDER):
        raise PermissionError("Void requires Manager or above")

    # In a route or service:
    require_capability(user, Capability.APPLY_DISCOUNT)
"""

from enum import StrEnum
from typing import Optional

from app.db.models import Role, StaffStatus, User
from app.services.base import PermissionError


# ─────────────────────────────────────────────────────────────────────────────
# Capability catalogue
# Every action in the system maps to exactly one Capability.
# ─────────────────────────────────────────────────────────────────────────────

class Capability(StrEnum):
    # Settings
    MANAGE_VENUE_SETTINGS = "manage_venue_settings"
    MANAGE_BRANCHES = "manage_branches"
    MANAGE_STAFF = "manage_staff"
    RESET_STAFF_PIN = "reset_staff_pin"

    # Product catalogue
    MANAGE_MENU = "manage_menu"
    MANAGE_CATEGORIES = "manage_categories"
    MANAGE_MODIFIERS = "manage_modifiers"
    MANAGE_STATIONS = "manage_stations"
    MANAGE_TAX_TEMPLATES = "manage_tax_templates"
    MANAGE_UNITS = "manage_units"

    # POS
    CREATE_ORDER = "create_order"
    ADD_ORDER_ITEM = "add_order_item"
    VOID_ORDER_ITEM = "void_order_item"
    VOID_ORDER = "void_order"
    APPLY_DISCOUNT = "apply_discount"
    APPLY_DISCOUNT_ABOVE_LIMIT = "apply_discount_above_limit"
    CLOSE_ORDER = "close_order"
    SEND_TO_KITCHEN = "send_to_kitchen"

    # Cash
    OPEN_CASH_SESSION = "open_cash_session"
    CLOSE_CASH_SESSION = "close_cash_session"
    ACCEPT_CASH_DISCREPANCY = "accept_cash_discrepancy"
    SAFE_DROP = "safe_drop"
    PAID_OUT = "paid_out"

    # Kitchen
    VIEW_KDS = "view_kds"
    BUMP_TICKET = "bump_ticket"
    ESCALATE_TICKET = "escalate_ticket"

    # Inventory
    VIEW_INVENTORY = "view_inventory"
    ADJUST_STOCK = "adjust_stock"
    RECEIVE_STOCK = "receive_stock"
    LOG_WASTE = "log_waste"

    # Reporting
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"

    # Printing
    PRINT_RECEIPT = "print_receipt"
    REPRINT_RECEIPT = "reprint_receipt"


# ─────────────────────────────────────────────────────────────────────────────
# Role → capabilities map
# Roles inherit from those below them in the hierarchy:
#   ADMIN > MANAGER > CASHIER / SERVER / KITCHEN_MANAGER > KITCHEN
# ─────────────────────────────────────────────────────────────────────────────

_KITCHEN_CAPS: frozenset[Capability] = frozenset({
    Capability.VIEW_KDS,
    Capability.BUMP_TICKET,
})

_KITCHEN_MANAGER_CAPS: frozenset[Capability] = _KITCHEN_CAPS | frozenset({
    Capability.ESCALATE_TICKET,
    Capability.MANAGE_STATIONS,
    Capability.VIEW_INVENTORY,
    Capability.LOG_WASTE,
})

_SERVER_CAPS: frozenset[Capability] = frozenset({
    Capability.CREATE_ORDER,
    Capability.ADD_ORDER_ITEM,
    Capability.SEND_TO_KITCHEN,
    Capability.VIEW_KDS,
    Capability.CLOSE_ORDER,
    Capability.PRINT_RECEIPT,
})

_CASHIER_CAPS: frozenset[Capability] = _SERVER_CAPS | frozenset({
    Capability.VOID_ORDER_ITEM,
    Capability.APPLY_DISCOUNT,
    Capability.OPEN_CASH_SESSION,
    Capability.CLOSE_CASH_SESSION,
    Capability.SAFE_DROP,
    Capability.PAID_OUT,
    Capability.REPRINT_RECEIPT,
    Capability.VIEW_INVENTORY,
})

_MANAGER_CAPS: frozenset[Capability] = (
    _CASHIER_CAPS | _KITCHEN_MANAGER_CAPS | frozenset({
        Capability.VOID_ORDER,
        Capability.APPLY_DISCOUNT_ABOVE_LIMIT,
        Capability.ACCEPT_CASH_DISCREPANCY,
        Capability.ADJUST_STOCK,
        Capability.RECEIVE_STOCK,
        Capability.VIEW_REPORTS,
        Capability.EXPORT_REPORTS,
        Capability.MANAGE_MENU,
        Capability.MANAGE_CATEGORIES,
        Capability.MANAGE_MODIFIERS,
        Capability.MANAGE_TAX_TEMPLATES,
        Capability.MANAGE_UNITS,
        Capability.RESET_STAFF_PIN,
    })
)

_ADMIN_CAPS: frozenset[Capability] = _MANAGER_CAPS | frozenset({
    Capability.MANAGE_VENUE_SETTINGS,
    Capability.MANAGE_BRANCHES,
    Capability.MANAGE_STAFF,
})

ROLE_CAPABILITIES: dict[Role, frozenset[Capability]] = {
    Role.ADMIN: _ADMIN_CAPS,
    Role.MANAGER: _MANAGER_CAPS,
    Role.CASHIER: _CASHIER_CAPS,
    Role.SERVER: _SERVER_CAPS,
    Role.KITCHEN_MANAGER: _KITCHEN_MANAGER_CAPS,
    Role.KITCHEN: _KITCHEN_CAPS,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_user_role(user: User) -> Optional[Role]:
    """Return the user's Role or None if not a staff member."""
    if user.staff_profile:
        return user.staff_profile.role
    return None


def can(user: User, capability: Capability) -> bool:
    """Return True if *user* holds *capability*."""
    role = get_user_role(user)
    if role is None:
        return False
    return capability in ROLE_CAPABILITIES.get(role, frozenset())


def require_capability(user: User, capability: Capability) -> None:
    """
    Assert that *user* holds *capability*.
    Raises PermissionError (→ HTTP 403) if not.
    """
    if not can(user, capability):
        role_name = get_user_role(user) or "unknown"
        raise PermissionError(
            f"Role '{role_name}' does not have capability '{capability}'."
        )


def is_branch_bound(role: Role) -> bool:
    """Return True for roles that may only operate within their own branch."""
    return role not in (Role.ADMIN,)


def assert_branch_access(user: User, branch_id: int) -> None:
    """
    Raise PermissionError if *user* attempts to operate on a branch they are
    not assigned to (for branch-bound roles).

    ADMINs are cross-branch — they always pass.
    """
    role = get_user_role(user)
    if role is None:
        raise PermissionError("Staff profile missing.")

    if not is_branch_bound(role):
        return  # ADMIN: cross-branch access

    staff_branch = user.staff_profile.branch_id if user.staff_profile else None
    if staff_branch != branch_id:
        raise PermissionError(
            f"You are not authorised to operate on branch {branch_id}."
        )


def assert_staff_active(user: User) -> None:
    """Raise PermissionError if the staff account is not ACTIVE."""
    from app.db.models import StaffStatus  # local import avoids circular dep
    if not user.staff_profile or user.staff_profile.status != StaffStatus.ACTIVE:
        raise PermissionError("Staff account is not active.")