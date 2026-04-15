"""
base.py — Shared service primitives
─────────────────────────────────────────────────────────────────────────────
Changes from v1:
  • Added ConflictError (HTTP 409) — was missing, causing import failures in
    settings_service.py and settings_product.py.
  • handle_service_errors now uses functools.wraps to preserve function
    signatures for FastAPI dependency injection.
  • Added to_money() helper (Decimal quantisation for financial values).
  • Tightened Generic[T] typing on BaseService.list() return type.
"""

import functools
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Generic, List, Optional, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")
MONEY_QUANT = Decimal("0.01")


# ─────────────────────────────────────────────────────────────────────────────
# Money helper
# ─────────────────────────────────────────────────────────────────────────────

def to_money(value: Decimal | int | float | str) -> Decimal:
    """Quantise any numeric value to 2 d.p. using ROUND_HALF_UP (financial standard)."""
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# Domain exceptions  (map to HTTP status in handle_service_errors)
# ─────────────────────────────────────────────────────────────────────────────

class ServiceError(Exception):
    """Base class for all service-layer errors."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(ServiceError):
    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found", "NOT_FOUND")


class ValidationError(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, "VALIDATION_ERROR")


class PermissionError(ServiceError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, "PERMISSION_DENIED")


class ConflictError(ServiceError):
    """Raised when a uniqueness constraint would be violated (HTTP 409)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "CONFLICT")


class LockedError(ServiceError):
    """Raised when an account or resource is temporarily locked (HTTP 423)."""

    def __init__(self, message: str) -> None:
        super().__init__(message, "LOCKED")


# ─────────────────────────────────────────────────────────────────────────────
# Error → HTTP mapping decorator
# ─────────────────────────────────────────────────────────────────────────────

def handle_service_errors(func):
    """
    Decorator: converts service-layer domain errors into FastAPI HTTPExceptions.

    Usage on route handlers or service methods called from routes:

        @router.post("/...")
        @handle_service_errors
        async def my_endpoint(...):
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any):
        try:
            return await func(*args, **kwargs)
        except NotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.message,
            ) from exc
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=exc.message,
            ) from exc
        except ConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc
        except LockedError as exc:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=exc.message,
            ) from exc
        except ServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.message,
            ) from exc

    return wrapper


# ─────────────────────────────────────────────────────────────────────────────
# Generic base service
# ─────────────────────────────────────────────────────────────────────────────

class BaseService(Generic[T]):
    """
    Thin CRUD base.  Domain services inherit from this and override / extend
    as needed.  Keeps boilerplate out of every service file.
    """

    model: type[T] | None = None

    def __init__(self, db: AsyncSession, current_user: Optional[Any] = None) -> None:
        self.db = db
        self.user = current_user
        if self.model is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must declare a `model` class attribute."
            )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def get(self, id: Any) -> Optional[T]:
        return await self.db.get(self.model, id)

    async def get_or_404(self, id: Any) -> T:
        instance = await self.get(id)
        if not instance:
            raise NotFoundError(self.model.__name__)
        return instance

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters: Any,
    ) -> List[T]:
        query = select(self.model)
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    async def create(self, **data: Any) -> T:
        instance = self.model(**data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: Any, **data: Any) -> T:
        instance = await self.get_or_404(id)
        for key, value in data.items():
            if value is not None and hasattr(instance, key):
                setattr(instance, key, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: Any) -> None:
        instance = await self.get_or_404(id)
        await self.db.delete(instance)
        await self.db.commit()