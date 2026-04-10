from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=32)
    timezone: str = Field(default="Africa/Nairobi", max_length=64)


class BranchRead(BaseModel):
    id: int
    name: str
    code: str
    address: str | None = None
    phone: str | None = None
    timezone: str
    is_active: bool

    model_config = {"from_attributes": True}

