"""
dependencies.py — FastAPI injectable dependencies
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  • Fixed import path: `from app.db.models import User` (was app.models.user).
  • `require_role` now accepts Role enum values directly (not raw strings).
  • Added `require_branch_access` — enforces MANAGER/CASHIER/SERVER/KITCHEN
    are scoped to their own branch (ADMIN is cross-branch).
  • Added `require_any_role` shorthand for the common single-role case.
  • Added `get_optional_user` for public endpoints that *can* authenticate.
"""

from typing import Callable, Optional

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.models import Role, User
from app.db.session import get_db
from app.services.auth import get_user_by_id


# ─────────────────────────────────────────────────────────────────────────────
# Core auth dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolves the Bearer token from the Authorization header to a User.
    Raises HTTP 401 on any auth failure.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    token = authorization.removeprefix("Bearer ")
    try:
        payload = verify_token(token, expected_type="access")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = await get_user_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )
    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Same as get_current_user but returns None instead of 401 when no valid
    token is present.  Use for public endpoints that optionally personalise
    responses for authenticated users.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Role-based access
# ─────────────────────────────────────────────────────────────────────────────

def require_role(*allowed_roles: Role) -> Callable:
    """
    Factory that returns a FastAPI dependency enforcing role membership.

    Usage:
        @router.post("/admin-only")
        async def my_endpoint(
            _: User = Depends(require_role(Role.ADMIN, Role.MANAGER))
        ):
            ...
    """

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        role = (
            current_user.staff_profile.role if current_user.staff_profile else None
        )
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Required roles: {[r.value for r in allowed_roles]}. "
                    f"Your role: {role}."
                ),
            )
        return current_user

    return checker


def require_any_role(role: Role) -> Callable:
    """Shorthand for a single required role."""
    return require_role(role)


# Convenience shorthands
require_admin = require_role(Role.ADMIN)
require_manager = require_role(Role.ADMIN, Role.MANAGER)
require_cashier = require_role(Role.ADMIN, Role.MANAGER, Role.CASHIER)
require_server = require_role(Role.ADMIN, Role.MANAGER, Role.CASHIER, Role.SERVER)
require_kitchen = require_role(
    Role.ADMIN,
    Role.MANAGER,
    Role.KITCHEN_MANAGER,
    Role.KITCHEN,
)


# ─────────────────────────────────────────────────────────────────────────────
# Branch-scope enforcement  (blueprint §4.3)
# ─────────────────────────────────────────────────────────────────────────────

def require_branch_access(branch_id_param: str = "branch_id") -> Callable:
    """
    Factory: reads `branch_id` from the path parameter named *branch_id_param*
    and verifies the current user is authorised to access that branch.

    ADMIN is always allowed.
    MANAGER / CASHIER / SERVER / KITCHEN are branch-bound.

    Usage:
        @router.get("/branches/{branch_id}/orders")
        async def list_orders(
            branch_id: int,
            user: User = Depends(require_branch_access()),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    async def checker(
        current_user: User = Depends(get_current_user),
        **path_params,
    ) -> User:
        from app.core.authz import assert_branch_access, assert_staff_active

        assert_staff_active(current_user)

        branch_id = path_params.get(branch_id_param)
        if branch_id is not None:
            try:
                assert_branch_access(current_user, int(branch_id))
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc

        return current_user

    return checker


# ─────────────────────────────────────────────────────────────────────────────
# Capability-based gate  (thin wrapper around authz.require_capability)
# ─────────────────────────────────────────────────────────────────────────────

def require_capability(capability: str) -> Callable:
    """
    FastAPI dependency that raises 403 if the current user's role lacks the
    named capability.

    Usage:
        @router.post("/orders/{order_id}/void")
        async def void_order(
            _: User = Depends(require_capability("void_order")),
            ...
        ):
    """
    from app.core.authz import Capability

    cap = Capability(capability)

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        from app.core.authz import require_capability as authz_require

        try:
            authz_require(current_user, cap)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        return current_user

    return checker