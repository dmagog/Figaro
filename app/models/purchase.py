from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class Purchase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_op_id: int = Field(index=True, description="ID операции во внешней системе")
    user_external_id: str = Field(index=True, description="ClientId из внешней системы")
    concert_id: int = Field(foreign_key="concert.id")
    purchased_at: datetime
    price: Optional[int] = None
