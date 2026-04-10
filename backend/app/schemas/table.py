from pydantic import BaseModel, Field

from app.models.enums import TableStatus


class TableCreate(BaseModel):
    branch_id: int
    table_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(default=4, ge=1, le=100)


class TableStatusUpdate(BaseModel):
    status: TableStatus


class TableRead(BaseModel):
    id: int
    branch_id: int
    table_number: str
    capacity: int
    status: TableStatus
    qr_code_token: str

    model_config = {"from_attributes": True}

