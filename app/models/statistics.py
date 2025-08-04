from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from typing import Optional
 
class Statistics(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)  # например: "routes_count", "users_count"
    value: int = Field(default=0)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) 