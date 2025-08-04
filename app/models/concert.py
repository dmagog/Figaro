from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timedelta

from .hall import Hall
from .artist import Artist, ConcertArtistLink
from .composition import Composition, ConcertCompositionLink
from .genre import Genre, ConcertGenreLink


class Concert(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    external_id: int = Field(index=True)
    name: str
    datetime: datetime
    duration: timedelta
    genre: Optional[str]
    price: Optional[int]
    is_family_friendly: bool = Field(default=False)
    tickets_available: bool = Field(default=True)
    tickets_left: Optional[int] = Field(default=None)  # Количество оставшихся билетов
    link: Optional[str]

    hall_id: int = Field(foreign_key="hall.id")
    hall: Optional[Hall] = Relationship()

    artists: List[Artist] = Relationship(back_populates="concerts", link_model=ConcertArtistLink)
    compositions: List[Composition] = Relationship(back_populates="concerts", link_model=ConcertCompositionLink)
    genres: List[Genre] = Relationship(back_populates="concerts", link_model=ConcertGenreLink)
