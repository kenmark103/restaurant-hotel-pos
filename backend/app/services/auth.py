from datetime import UTC, datetime

import httpx
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.db.session import get_db
from app.models.customer_profile import CustomerProfile
from app.models.enums import AuthProvider, Role, StaffStatus, UserType
from app.models.staff_profile import StaffProfile
from app.models.user import User
from app.schemas.auth import StaffLoginRequest, TokenPair, UserSession

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_initial_admin(self) -> None:
        result = await self.db.execute(select(User).where(User.email == settings.INITIAL_ADMIN_EMAIL.lower()))
        if result.scalar_one_or_none():
            return

        admin_user = User(
            email=settings.INITIAL_ADMIN_EMAIL.lower(),
            full_name="Initial Admin",
            password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            user_type=UserType.STAFF,
            auth_provider=AuthProvider.LOCAL,
            is_active=True,
        )
        self.db.add(admin_user)
        await self.db.flush()
        self.db.add(StaffProfile(user_id=admin_user.id, role=Role.ADMIN, status=StaffStatus.ACTIVE))
        await self.db.commit()

    async def login_staff(self, payload: StaffLoginRequest) -> TokenPair:
        await self.ensure_initial_admin()
        result = await self.db.execute(
            select(User).where(User.email == payload.email.lower(), User.user_type == UserType.STAFF)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid staff credentials.")

        staff_result = await self.db.execute(select(StaffProfile).where(StaffProfile.user_id == user.id))
        staff_profile = staff_result.scalar_one_or_none()
        if not staff_profile or staff_profile.status != StaffStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff account is not active.")

        user.last_login_at = datetime.now(UTC)
        await self.db.commit()
        return self._token_pair(user.id)

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        try:
            subject = decode_token(refresh_token, "refresh")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        return self._token_pair(int(subject))

    async def login_customer_with_google(self, code: str) -> TokenPair:
        if not settings.google_oauth_enabled:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth is not configured.")

        async with httpx.AsyncClient(timeout=15) as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            google_access_token = token_response.json()["access_token"]

            profile_response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()

        email = str(profile["email"]).lower()
        google_subject = str(profile["sub"])
        full_name = profile.get("name") or email

        customer_query = await self.db.execute(
            select(User).join(CustomerProfile).where(or_(User.email == email, CustomerProfile.google_subject == google_subject))
        )
        user = customer_query.scalar_one_or_none()

        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                user_type=UserType.CUSTOMER,
                auth_provider=AuthProvider.GOOGLE,
                is_active=True,
            )
            self.db.add(user)
            await self.db.flush()
            self.db.add(
                CustomerProfile(
                    user_id=user.id,
                    google_subject=google_subject,
                    preferences={"source": "google_oauth"},
                )
            )
        else:
            user.full_name = full_name
            user.auth_provider = AuthProvider.GOOGLE
            user.is_active = True
            profile_query = await self.db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
            customer_profile = profile_query.scalar_one_or_none()
            if customer_profile is None:
                self.db.add(CustomerProfile(user_id=user.id, google_subject=google_subject))
            else:
                customer_profile.google_subject = google_subject

        user.last_login_at = datetime.now(UTC)
        await self.db.commit()
        return self._token_pair(user.id)

    def _token_pair(self, user_id: int) -> TokenPair:
        subject = str(user_id)
        return TokenPair(access_token=create_access_token(subject), refresh_token=create_refresh_token(subject))


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> UserSession:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    try:
        subject = decode_token(authorization.split(" ", 1)[1], "access")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    result = await db.execute(select(User).where(User.id == int(subject)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

    session = UserSession(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        user_type=user.user_type,
        auth_provider=user.auth_provider,
    )

    if user.user_type == UserType.STAFF:
        staff_result = await db.execute(select(StaffProfile).where(StaffProfile.user_id == user.id))
        staff_profile = staff_result.scalar_one_or_none()
        if staff_profile:
            session.role = staff_profile.role
            session.staff_status = staff_profile.status
            session.branch_code = staff_profile.branch_code
    else:
        customer_result = await db.execute(select(CustomerProfile).where(CustomerProfile.user_id == user.id))
        customer_profile = customer_result.scalar_one_or_none()
        if customer_profile:
            session.loyalty_points = customer_profile.loyalty_points

    return session
