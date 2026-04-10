from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.schemas.branch import BranchCreate


async def list_branches(db: AsyncSession) -> list[Branch]:
    result = await db.execute(select(Branch).order_by(Branch.name.asc()))
    return result.scalars().all()


async def get_branch_by_code(db: AsyncSession, code: str) -> Branch | None:
    result = await db.execute(select(Branch).where(Branch.code == code))
    return result.scalar_one_or_none()


async def create_branch(db: AsyncSession, payload: BranchCreate) -> Branch:
    branch = Branch(
        name=payload.name,
        code=payload.code.upper(),
        address=payload.address,
        phone=payload.phone,
        timezone=payload.timezone,
    )
    db.add(branch)
    await db.commit()
    await db.refresh(branch)
    return branch

