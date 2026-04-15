"""
override_service.py — Manager override grant lifecycle
─────────────────────────────────────────────────────────────────────────────
Blueprint §4.4 — Manager Override via PIN:

  1. Cashier requests an override for a privileged action (void, discount, etc.)
  2. Manager enters their PIN on the same terminal
  3. A ManagerOverrideGrant row is created (TTL = 2 minutes, single-use)
  4. The grant_id is passed with the protected action
  5. The protected endpoint calls consume_grant() — validates and marks used_at
  6. An AuditLog row records both the actor and the approving manager

Grants expire after GRANT_TTL_SECONDS regardless of whether they are used.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.models import (
    AuditAction,
    AuditLog,
    ManagerOverrideGrant,
    OverrideAction,
    StaffStatus,
    StaffProfile,
    User,
)
from app.services.base import BaseService, NotFoundError, PermissionError, ValidationError
from app.core.security import verify_pin

GRANT_TTL_SECONDS = 120   # 2-minute window


class OverrideService(BaseService[ManagerOverrideGrant]):
    model = ManagerOverrideGrant

    async def request_grant(
        self,
        requesting_user_id: int,
        branch_id: int,
        action: OverrideAction,
        manager_pin: str,
        entity_type: str | None = None,
        entity_id: int | None = None,
        reason: str | None = None,
    ) -> ManagerOverrideGrant:
        """
        Validate the manager PIN for this branch, then create a short-lived
        ManagerOverrideGrant.  The grant_id is returned to the client for use
        in the subsequent protected action.
        """
        # Find an ACTIVE manager/admin on this branch with a matching PIN
        manager = await self._authenticate_manager_pin(branch_id, manager_pin)

        now = datetime.now(UTC)
        grant = ManagerOverrideGrant(
            branch_id=branch_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            granted_by_id=manager.id,
            requested_by_id=requesting_user_id,
            expires_at=now + timedelta(seconds=GRANT_TTL_SECONDS),
        )
        self.db.add(grant)
        await self.db.flush()

        self.db.add(AuditLog(
            branch_id=branch_id,
            actor_id=requesting_user_id,
            approved_by_id=manager.id,
            action=AuditAction.DISCOUNT_APPLIED,   # closest generic; swap to OVERRIDE_GRANTED if added to AuditAction
            entity_type=entity_type,
            entity_id=entity_id,
            payload={
                "override_action": action,
                "reason": reason,
                "grant_id": grant.id,
                "expires_at": grant.expires_at.isoformat(),
            },
        ))

        await self.db.commit()
        await self.db.refresh(grant)
        return grant

    async def consume_grant(
        self,
        grant_id: int,
        expected_action: OverrideAction,
        consuming_user_id: int,
    ) -> ManagerOverrideGrant:
        """
        Validate and consume (mark as used) an override grant.

        Raises ValidationError if:
          - Grant not found
          - Already used
          - Expired
          - Action mismatch
          - Requesting user mismatch
        """
        grant = await self.db.get(ManagerOverrideGrant, grant_id)
        if not grant:
            raise NotFoundError("ManagerOverrideGrant")
        if grant.used_at is not None:
            raise ValidationError("Override grant has already been used.")
        if grant.expires_at <= datetime.now(UTC):
            raise ValidationError("Override grant has expired. Request a new one.")
        if grant.action != expected_action:
            raise ValidationError(
                f"Grant is for action '{grant.action}', not '{expected_action}'."
            )
        if grant.requested_by_id != consuming_user_id:
            raise PermissionError("Override grant was issued for a different user.")

        grant.used_at = datetime.now(UTC)
        await self.db.commit()
        return grant

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _authenticate_manager_pin(self, branch_id: int, pin: str) -> User:
        """
        Find an ACTIVE Manager or Admin on this branch whose PIN matches.
        Raises PermissionError if no match found.
        """
        from app.db.models import Role
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(User)
            .options(selectinload(User.staff_profile))
            .join(StaffProfile)
            .where(
                StaffProfile.branch_id == branch_id,
                StaffProfile.status == StaffStatus.ACTIVE,
                StaffProfile.role.in_([Role.ADMIN, Role.MANAGER]),
                StaffProfile.pin_hash.is_not(None),
                User.is_active == True,
            )
        )
        candidates = result.scalars().all()

        now = datetime.now(UTC)
        for user in candidates:
            profile = user.staff_profile
            # Skip locked accounts
            if profile.pin_locked_until and profile.pin_locked_until > now:
                continue
            if verify_pin(pin, profile.pin_hash):
                # Reset failed attempts on success
                profile.pin_failed_attempts = 0
                profile.pin_locked_until = None
                await self.db.commit()
                return user

        raise PermissionError("Invalid manager PIN or no manager available at this branch.")