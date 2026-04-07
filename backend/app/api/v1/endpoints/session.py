from fastapi import APIRouter, Depends

from app.schemas.auth import UserSession
from app.services.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserSession)
async def me(current_user: UserSession = Depends(get_current_user)) -> UserSession:
    return current_user
