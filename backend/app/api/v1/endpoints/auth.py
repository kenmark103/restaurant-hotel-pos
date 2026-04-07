from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import GoogleStartResponse, RefreshRequest, StaffLoginRequest, TokenPair
from app.services.auth import AuthService

router = APIRouter()


@router.post("/staff/login", response_model=TokenPair)
async def staff_login(payload: StaffLoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await AuthService(db).login_staff(payload)


@router.post("/staff/refresh", response_model=TokenPair)
async def refresh_staff_session(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    return await AuthService(db).refresh_tokens(payload.refresh_token)


@router.post("/logout")
async def logout() -> dict[str, str]:
    return {"message": "Logout acknowledged. Discard the client tokens."}


@router.post("/customers/google/start", response_model=GoogleStartResponse)
async def customer_google_start(request: Request) -> GoogleStartResponse:
    if not settings.google_oauth_enabled:
        return GoogleStartResponse(
            enabled=False,
            authorization_url=None,
            message="Google OAuth is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable it.",
        )

    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
            "state": str(request.base_url),
        }
    )
    return GoogleStartResponse(
        enabled=True,
        authorization_url=f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
        message="Open the authorization URL to continue Google sign-in.",
    )


@router.get("/customers/google/callback", name="customer_google_callback")
async def customer_google_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing authorization code.")
    tokens = await AuthService(db).login_customer_with_google(code)
    redirect_url = f"{settings.FRONTEND_URL}/account/login?access_token={tokens.access_token}&refresh_token={tokens.refresh_token}"
    return RedirectResponse(url=redirect_url)
