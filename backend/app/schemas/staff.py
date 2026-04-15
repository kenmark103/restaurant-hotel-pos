from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.db.models import Role, StaffStatus


class StaffInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Role
    branch_id: Optional[int] = None


class StaffUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[Role] = None
    branch_id: Optional[int] = None


class StaffRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    status: StaffStatus
    branch_id: Optional[int] = None
    has_pin: bool = False

    model_config = {"from_attributes": True}


class StaffActivateRequest(BaseModel):
    """Body for the staff activation endpoint (/staff/activate)."""

    token: str
    password: str = Field(min_length=8, description="Initial password for email login")


class AdminSetPinRequest(BaseModel):
    """Manager/Admin sets or resets a staff member's PIN."""

    pin: str = Field(min_length=5, max_length=5)
    staff_user_id: int

    # Optional manager-override context (required when discount_auth is ON)
    override_grant_id: Optional[int] = None