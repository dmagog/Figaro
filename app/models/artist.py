# models/artist.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class ConcertArtistLink(SQLModel, table=True, extend_existing=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    artist_id: int = Field(foreign_key="artist.id", primary_key=True)


class Artist(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    is_special: bool = Field(default=False)

    concerts: List["Concert"] = Relationship(back_populates="artists", link_model=ConcertArtistLink)
