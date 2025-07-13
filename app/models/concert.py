from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timedelta

from .hall import Hall  # относительный импорт

class Concert(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: int = Field(index=True, description="ID концерта во внешней системе (ShowId)")
    name: str = Field(index=True, description="Название концерта")
    datetime: datetime
    duration: timedelta  = Field(default=timedelta(minutes=45), description="Продолжительность концерта")
    genre: Optional[str] = Field(default=None, description="Жанр концерта")
    price: Optional[int] = Field(default=None, description="Цена билета")
    is_family_friendly: bool = Field(default=False, description="Подходит для семейного посещения")
    tickets_available: bool = Field(default=True, description="Билеты в продаже")
    link: Optional[str] = Field(default=None, description="Ссылка на страницу концерта")

    hall_id: int = Field(foreign_key="hall.id")
