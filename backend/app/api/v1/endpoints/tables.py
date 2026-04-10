from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.table import TableCreate, TableRead, TableStatusUpdate
from app.services.table import create_table, list_tables, update_table_status

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("/", response_model=list[TableRead])
async def get_tables(
    branch_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager", "cashier", "server"])),
) -> list[TableRead]:
    return await list_tables(db, branch_id=branch_id)


@router.post("/", response_model=TableRead, status_code=status.HTTP_201_CREATED)
async def create_table_endpoint(
    payload: TableCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager"])),
) -> TableRead:
    return await create_table(db, payload)


@router.patch("/{table_id}/status", response_model=TableRead)
async def update_table_status_endpoint(
    table_id: int,
    payload: TableStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "manager", "cashier", "server"])),
) -> TableRead:
    table = await update_table_status(db, table_id, payload.status)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found.")
    return table

