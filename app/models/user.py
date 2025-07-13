from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from sqlalchemy import Column, JSON


class UserBase(SQLModel):
    external_id: Optional[str] = Field(default=None, description="ID во внешней системе")
    email: str
    name: Optional[str] = None
    preferences: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    role: str = Field(default="user")


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    preferences: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    role: Optional[str] = None


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # routes: List[Route] = Relationship(back_populates="user")
