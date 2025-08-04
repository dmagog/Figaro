from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Purchase(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_op_id: int = Field(index=True, description="ID операции во внешней системе")
    user_external_id: str = Field(index=True, description="ClientId из внешней системы")
    concert_id: int = Field(foreign_key="concert.id")
    purchased_at: datetime
    price: Optional[int] = None


class Customer(BaseModel):
    user_external_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_superuser: Optional[bool] = None
    total_purchases: int
    total_spent: int
    unique_concerts: int
    unique_days: int
    route_match: dict
