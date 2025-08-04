from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timedelta
from sqlalchemy import Column, JSON
from pydantic import EmailStr, validator
from uuid import uuid4


class UserBase(SQLModel):
    external_id: Optional[str] = Field(default=None, description="ID во внешней системе")
    email: str
    name: Optional[str] = None
    preferences: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    role: str = Field(default="user")
    telegram_id: Optional[int] = Field(default=None, description="Telegram user ID")
    telegram_username: Optional[str] = Field(default=None, description="Telegram username")


class UserCreate(UserBase):
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and v.strip() == "":
            raise ValueError('Name cannot be empty')
        return v


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
    telegram_id: Optional[int] = None


class User(UserBase, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # routes: List[Route] = Relationship(back_populates="user")


class TelegramLinkCode(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    code: str = Field(default_factory=lambda: str(uuid4()), index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=lambda: datetime.utcnow())

    @staticmethod
    def generate_expiry(minutes: int = 10):
        return datetime.utcnow() + timedelta(minutes=minutes)
