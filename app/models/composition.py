# models/composition.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship


class Author(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)


class ConcertCompositionLink(SQLModel, table=True, extend_existing=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    composition_id: int = Field(foreign_key="composition.id", primary_key=True)


class Composition(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    author_id: int = Field(foreign_key="author.id")
    author: Optional[Author] = Relationship()

    concerts: List["Concert"] = Relationship(back_populates="compositions", link_model=ConcertCompositionLink)
