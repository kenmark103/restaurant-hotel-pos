"""
settings_service.py — Venue & Branch configuration
─────────────────────────────────────────────────────────────────────────────
SettingsService    – CRUD for VenueSettings singleton + Branch management
PublicSettingsService – Read-only, unauthenticated customer-facing data
"""
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Branch, BranchSettings, VenueSettings
from app.services.base import BaseService, ConflictError, NotFoundError, ValidationError


class SettingsService(BaseService[VenueSettings]):
    model = VenueSettings
    _SINGLETON_ID = "default"

    # ═══════════════════════════════════════════════════════════════════════════
    # VENUE SETTINGS  (singleton)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_venue_settings(self) -> VenueSettings:
        """Return the singleton VenueSettings row, creating it on first call."""
        settings = await self.get(self._SINGLETON_ID)
        if not settings:
            settings = VenueSettings(id=self._SINGLETON_ID)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return settings

    async def update_venue_settings(self, **updates) -> VenueSettings:
        """Partial update of venue settings.  Caller must hold ADMIN role."""
        settings = await self.get_venue_settings()
        for key, value in updates.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)
        settings.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    # ═══════════════════════════════════════════════════════════════════════════
    # BRANCH SETTINGS  (per-branch overrides)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_branch_settings(self, branch_id: int) -> Optional[BranchSettings]:
        result = await self.db.execute(
            select(BranchSettings).where(BranchSettings.branch_id == branch_id)
        )
        return result.scalar_one_or_none()

    async def upsert_branch_settings(self, branch_id: int, **updates) -> BranchSettings:
        """Create or partially update branch-level settings."""
        # Validate branch exists
        branch = await self.db.get(Branch, branch_id)
        if not branch:
            raise NotFoundError("Branch")

        settings = await self.get_branch_settings(branch_id)
        if not settings:
            settings = BranchSettings(branch_id=branch_id)
            self.db.add(settings)

        for key, value in updates.items():
            if value is not None and hasattr(settings, key):
                setattr(settings, key, value)

        await self.db.commit()
        await self.db.refresh(settings)
        return settings

    # ═══════════════════════════════════════════════════════════════════════════
    # EFFECTIVE SETTINGS  (venue defaults merged with branch overrides)
    # ═══════════════════════════════════════════════════════════════════════════

    async def get_effective_settings(self, branch_id: Optional[int] = None) -> dict:
        """
        Returns a flat dict of all settings with branch overrides applied.
        This is the canonical source of truth for tax rates, feature flags, etc.
        """
        venue = await self.get_venue_settings()
        effective = {
            col.name: getattr(venue, col.name)
            for col in venue.__table__.columns
            if col.name != "id"
        }

        if branch_id:
            branch_override = await self.get_branch_settings(branch_id)
            if branch_override:
                if branch_override.receipt_footer:
                    effective["receipt_footer"] = branch_override.receipt_footer
                if branch_override.tax_rate is not None:
                    effective["tax_rate"] = branch_override.tax_rate

        return effective

    # ═══════════════════════════════════════════════════════════════════════════
    # BRANCH MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    async def list_branches(self, active_only: bool = True) -> list[Branch]:
        query = select(Branch).order_by(Branch.name)
        if active_only:
            query = query.where(Branch.is_active == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_branch(self, branch_id: int) -> Branch:
        branch = await self.db.get(Branch, branch_id)
        if not branch:
            raise NotFoundError("Branch")
        return branch

    async def create_branch(
        self,
        name: str,
        code: str,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        timezone: str = "Africa/Nairobi",
    ) -> Branch:
        # Enforce unique code
        existing = await self.db.execute(select(Branch).where(Branch.code == code.upper()))
        if existing.scalar_one_or_none():
            raise ConflictError(f"Branch code '{code}' already exists")

        branch = Branch(
            name=name,
            code=code.upper(),
            address=address,
            phone=phone,
            timezone=timezone,
        )
        self.db.add(branch)
        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def update_branch(self, branch_id: int, **updates) -> Branch:
        branch = await self.get_branch(branch_id)

        if "code" in updates and updates["code"]:
            new_code = updates["code"].upper()
            conflict = await self.db.execute(
                select(Branch).where(Branch.code == new_code, Branch.id != branch_id)
            )
            if conflict.scalar_one_or_none():
                raise ConflictError(f"Branch code '{new_code}' already in use")
            updates["code"] = new_code

        for key, value in updates.items():
            if value is not None and hasattr(branch, key):
                setattr(branch, key, value)

        await self.db.commit()
        await self.db.refresh(branch)
        return branch

    async def deactivate_branch(self, branch_id: int) -> Branch:
        branch = await self.get_branch(branch_id)
        branch.is_active = False
        await self.db.commit()
        return branch


# ─────────────────────────────────────────────────────────────────────────────
# Public (unauthenticated) settings — customer-facing display
# ─────────────────────────────────────────────────────────────────────────────

class PublicSettingsService:
    """Read-only settings safe to expose without authentication."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_public_settings(self) -> dict:
        result = await self.db.execute(select(VenueSettings))
        venue = result.scalar_one_or_none()
        if not venue:
            return {}

        return {
            "restaurant_name": venue.restaurant_name,
            "logo_url": venue.logo_url,
            "primary_color": venue.primary_color,
            "secondary_color": venue.secondary_color,
            "currency": venue.currency,
            "currency_symbol": venue.currency_symbol,
            "timezone": venue.timezone,
            "theme": venue.theme,
            "enable_loyalty": venue.enable_loyalty,
            "enable_reservations": venue.enable_reservations,
            "receipt_footer": venue.receipt_footer,
        }