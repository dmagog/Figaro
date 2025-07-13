from typing import Optional
from sqlmodel import SQLModel, Field


class Hall(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Название зала")
    concert_count: int = Field(description="Количество концертов в зале")
    address: Optional[str] = Field(default=None, description="Адрес зала")
    latitude: Optional[float] = Field(default=None, description="Широта (latitude)")
    longitude: Optional[float] = Field(default=None, description="Долгота (longitude)")
    seats: int = Field(default=0, description="Количество мест в зале")
