# models/genre.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ConcertGenreLink(SQLModel, table=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    genre_id: int = Field(foreign_key="genre.id", primary_key=True)


class Genre(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    concerts: List["Concert"] = Relationship(back_populates="genres", link_model=ConcertGenreLink) 