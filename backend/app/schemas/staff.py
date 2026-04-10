from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Role, StaffStatus


class StaffInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    role: Role
    branch_id: int | None = None


class StaffActivateRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class StaffRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    status: StaffStatus
    branch_id: int | None = None


class StaffActivationResponse(BaseModel):
    detail: str
    activation_token: str | None = None
