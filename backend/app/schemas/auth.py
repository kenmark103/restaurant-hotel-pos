from pydantic import BaseModel, EmailStr, Field

from app.models.enums import AuthProvider, Role, StaffStatus, UserType


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class GoogleStartResponse(BaseModel):
    enabled: bool
    authorization_url: str | None
    message: str


class UserSession(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    user_type: UserType
    auth_provider: AuthProvider
    role: Role | None = None
    staff_status: StaffStatus | None = None
    branch_code: str | None = None
    loyalty_points: int | None = None
