from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import set_refresh_cookie, clear_refresh_cookie, decode_refresh_cookie
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginResponse,
    PinLoginRequest,
    StaffLoginRequest,
    UserSession,
)
from app.services.auth import (
    authenticate_staff,
    authenticate_staff_by_pin,
    build_login_response,
    build_user_session,
    login_customer_with_google,
    revoke_all_refresh_tokens,
    rotate_refresh_token,
)

router = APIRouter()


# ── Staff: email + password ───────────────────────────────────────────────────

@router.post("/staff/login", response_model=LoginResponse)
async def staff_login(
    payload: StaffLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_staff(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

    login_resp, raw_refresh = await build_login_response(
        db, user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_refresh_cookie(response, raw_refresh)
    return login_resp


# ── Staff: 5-digit PIN (primary POS terminal login) ───────────────────────────

@router.post("/pin-login", response_model=LoginResponse)
async def pin_login(
    payload: PinLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticate_staff_by_pin(db, payload.branch_id, payload.pin)
    except ValueError as exc:
        code = status.HTTP_423_LOCKED if "locked" in str(exc).lower() else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=code, detail=str(exc))

    login_resp, raw_refresh = await build_login_response(
        db, user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    set_refresh_cookie(response, raw_refresh)
    return login_resp


# ── Token refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = decode_refresh_cookie(request)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")

    try:
        user, new_raw = await rotate_refresh_token(
            db, raw_token,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    login_resp, new_refresh = await build_login_response(db, user)
    set_refresh_cookie(response, new_refresh)
    return login_resp


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_all_refresh_tokens(db, current_user.id)
    clear_refresh_cookie(response)


# ── Session info ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserSession)
async def get_me(current_user: User = Depends(get_current_user)):
    return build_user_session(current_user)


# ── Google OAuth (customers) ──────────────────────────────────────────────────

@router.get("/customers/google/callback")
async def google_callback(
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        token_resp, raw_refresh = await login_customer_with_google(db, code)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    set_refresh_cookie(response, raw_refresh)
    return token_resp