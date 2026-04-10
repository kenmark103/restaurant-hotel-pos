from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.branch import BranchCreate, BranchRead
from app.services.branch import create_branch, get_branch_by_code, list_branches

router = APIRouter(prefix="/branches", tags=["branches"])


@router.get("/", response_model=list[BranchRead])
async def get_branches(db: AsyncSession = Depends(get_db)) -> list[BranchRead]:
    return await list_branches(db)


@router.post("/", response_model=BranchRead, status_code=status.HTTP_201_CREATED)
async def create_branch_endpoint(
    payload: BranchCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> BranchRead:
    existing = await get_branch_by_code(db, payload.code.upper())
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Branch code already exists.")
    return await create_branch(db, payload)

