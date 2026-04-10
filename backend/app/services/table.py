from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TableStatus
from app.models.table import Table
from app.schemas.table import TableCreate


async def list_tables(db: AsyncSession, branch_id: int | None = None) -> list[Table]:
    statement = select(Table).order_by(Table.table_number.asc())
    if branch_id is not None:
        statement = statement.where(Table.branch_id == branch_id)
    result = await db.execute(statement)
    return result.scalars().all()


async def create_table(db: AsyncSession, payload: TableCreate) -> Table:
    table = Table(
        branch_id=payload.branch_id,
        table_number=payload.table_number,
        capacity=payload.capacity,
    )
    db.add(table)
    await db.commit()
    await db.refresh(table)
    return table


async def update_table_status(db: AsyncSession, table_id: int, status: TableStatus) -> Table | None:
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if table is None:
        return None
    table.status = status
    await db.commit()
    await db.refresh(table)
    return table
