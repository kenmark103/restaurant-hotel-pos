from pydantic import BaseModel, EmailStr, Field

from app.db.models import AuthProvider, Role, StaffStatus, UserType


class StaffLoginRequest(BaseModel):
    """Email + password login (fallback for first setup or manager)"""
    email: EmailStr
    password: str = Field(min_length=8)


class PinLoginRequest(BaseModel):
    """Primary POS login — 5-digit numeric PIN (Blueprint v2 §4.2 B)"""
    branch_id: int
    pin: str = Field(
        ...,
        min_length=5,
        max_length=5,
        pattern=r"^\d{5}$",        
        description="5-digit numeric PIN unique per branch"
    )


class AccessTokenResponse(BaseModel):
    """Minimal token response (used by refresh endpoint)"""
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Full response returned by BOTH password login AND pin-login
    
    Used by frontend PIN Pad → Zustand session hydration
    """
    access_token: str
    token_type: str = "bearer"
    user: "UserSession"          # forward reference


class GoogleStartResponse(BaseModel):
    """OAuth2 flow helper"""
    enabled: bool
    authorization_url: str | None = None
    message: str


class UserSession(BaseModel):
    """Complete session data sent to frontend after any successful login"""
    id: int
    email: EmailStr
    full_name: str
    user_type: UserType
    auth_provider: AuthProvider
    role: Role | None = None
    staff_status: StaffStatus | None = None
    branch_id: int | None = None
    loyalty_points: int | None = None


# Required for Pydantic v2 forward reference
LoginResponse.model_rebuild()