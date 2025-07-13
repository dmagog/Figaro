from typing import Optional
from sqlmodel import SQLModel, Field


class Hall(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Название зала")
    concert_count: int = Field(description="Количество концертов в зале")
    address: Optional[str] = Field(default=None, description="Адрес зала")
    latitude: Optional[float] = Field(default=None, description="Широта (latitude)")
    longitude: Optional[float] = Field(default=None, description="Долгота (longitude)")




# class Hall(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str = Field(index=True)
#     concert_count: int
#     address: Optional[str] = None
#     latitude: Optional[float] = None
#     longitude: Optional[float] = None
