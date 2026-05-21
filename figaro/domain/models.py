"""Доменная модель v3 (SQLModel). Скоуп по фестивалю (festival_id), см. docs/02-domain-model.md.

Примечания реализации:
- единый внутренний `id` (BIGINT/autoincrement); внешние ключи источников — отдельные поля;
- длительности храним как `*_min` (int, минуты) — простота вместо INTERVAL;
- деньги — `*_kopecks` (int).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


class Festival(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    year: int
    sales_start_on: date
    starts_on: date
    ends_on: date
    timezone: str = "Europe/Moscow"
    status: str = "draft"  # draft | active | archived
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Hall(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "name", name="uq_hall_festival_name"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    name: str
    address: Optional[str] = None
    seats: int = 0
    lat: Optional[float] = None
    lon: Optional[float] = None


class HallTransition(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "from_hall_id", "to_hall_id",
                                       name="uq_transition"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    from_hall_id: int = Field(foreign_key="hall.id", index=True)
    to_hall_id: int = Field(foreign_key="hall.id", index=True)
    minutes: int


class Artist(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "name", name="uq_artist"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    name: str
    is_special: bool = False


class Author(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "name", name="uq_author"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    name: str


class Composition(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "author_id", "title", name="uq_composition"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    author_id: int = Field(foreign_key="author.id", index=True)
    title: str


class Genre(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "name", name="uq_genre"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    name: str
    description: Optional[str] = None


class Program(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "signature", name="uq_program"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    signature: str  # хеш нормализованного множества (автор, произведение)


class FestivalDay(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "day", name="uq_festivalday"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    day: date
    first_concert_at: Optional[datetime] = None
    last_concert_at: Optional[datetime] = None
    last_concert_ends_at: Optional[datetime] = None
    concert_count: int = 0


class Concert(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "show_num", name="uq_concert_shownum"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    show_num: int = Field(index=True)              # порядковый № внутри фестиваля
    crm_show_id: Optional[int] = Field(default=None, index=True)  # id в CRM (для покупок/наличия)
    title: str
    hall_id: int = Field(foreign_key="hall.id", index=True)
    festival_day_id: Optional[int] = Field(default=None, foreign_key="festivalday.id", index=True)
    starts_at: datetime
    duration_min: int
    price_kopecks: int = 0
    is_family_friendly: bool = False
    capacity: int = 0
    program_id: Optional[int] = Field(default=None, foreign_key="program.id", index=True)


class OffProgram(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    external_num: Optional[int] = None
    title: str
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    duration_min: Optional[int] = None
    hall_id: Optional[int] = Field(default=None, foreign_key="hall.id")
    fmt: Optional[str] = None
    is_recommended: bool = False
    link: Optional[str] = None


class Purchase(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "external_op_id", name="uq_purchase_op"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    external_op_id: int = Field(index=True)
    customer_external_id: str = Field(index=True)  # ClientId (псевдоним, не ПДн)
    concert_id: int = Field(foreign_key="concert.id", index=True)
    purchased_at: datetime
    price_kopecks: int = 0


# --- наличие билетов (состояние; движок curve/replay — этап 5) ---
class ConcertAvailability(SQLModel, table=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    is_on_sale: bool = True
    tickets_left: Optional[int] = None
    source: str = "crm_import"  # crm_import | sim_curve | sim_replay
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AvailabilitySnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    concert_id: int = Field(foreign_key="concert.id", index=True)
    at: datetime = Field(index=True)
    tickets_left: Optional[int] = None
    is_on_sale: bool = True
    source: str = "crm_import"


class SimState(SQLModel, table=True):
    festival_id: int = Field(foreign_key="festival.id", primary_key=True)
    availability_mode: str = "sim_curve"  # sim_curve | sim_replay | crm_import
    seed: int = 42


class OutboxMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: str  # concert_reminder | availability_alert
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    scheduled_for: datetime
    status: str = "pending"  # pending | sent | failed
    attempts: int = 0
    next_attempt_at: Optional[datetime] = None
    idempotency_key: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None


# --- маршруты (предрасчёт, этап 2) ---
class Archetype(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("festival_id", "key", name="uq_archetype"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    key: str            # marathon | comfort | explorer | deep
    title: str
    description: Optional[str] = None


class DayRoute(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    festival_day_id: int = Field(foreign_key="festivalday.id", index=True)
    archetype_id: Optional[int] = Field(default=None, foreign_key="archetype.id", index=True)
    # аддитивные агрегаты
    concerts_count: int = 0
    halls_count: int = 0
    show_minutes: int = 0
    transition_minutes: int = 0
    wait_minutes: int = 0
    cost_kopecks: int = 0
    hall_changes: int = 0
    # признаки (нормируются при ранжировании)
    comfort_score: float = 0.0
    diversity_score: float = 0.0


class DayRouteConcert(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("day_route_id", "concert_id", name="uq_dayrouteconcert"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    day_route_id: int = Field(foreign_key="dayroute.id", index=True)
    concert_id: int = Field(foreign_key="concert.id", index=True)
    position: int = 0


# --- пользователи и доступ (этап 3) ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    email_verified: bool = False
    name: Optional[str] = None
    hashed_password: str
    role: str = "user"  # user | researcher | admin
    is_active: bool = True
    consent_at: Optional[datetime] = None
    marketing_consent: bool = False
    failed_login_count: int = 0
    locked_until: Optional[datetime] = None
    telegram_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserPreferences(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    festival_id: int = Field(foreign_key="festival.id", primary_key=True)
    pace: Optional[str] = None             # marathon | balanced | relaxed
    interest_vector: Optional[str] = None  # new | deep
    available_days: list = Field(default_factory=list, sa_column=Column(JSON))
    time_windows: list = Field(default_factory=list, sa_column=Column(JSON))
    favorite_author_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    favorite_genre_ids: list = Field(default_factory=list, sa_column=Column(JSON))
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AuthToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kind: str  # verify | reset
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    used: bool = False


class UserSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    revoked: bool = False


class RouteSheet(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    festival_id: int = Field(foreign_key="festival.id", index=True)
    title: Optional[str] = None
    source: str = "manual"  # from_archetype | manual | split_from_purchases
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RouteSheetItem(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("route_sheet_id", "concert_id", name="uq_sheetitem"),)
    id: Optional[int] = Field(default=None, primary_key=True)
    route_sheet_id: int = Field(foreign_key="routesheet.id", index=True)
    concert_id: int = Field(foreign_key="concert.id", index=True)
    is_pinned: bool = False
    position: int = 0


# --- link-таблицы (M2M) ---
class ConcertArtist(SQLModel, table=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    artist_id: int = Field(foreign_key="artist.id", primary_key=True)


class ConcertComposition(SQLModel, table=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    composition_id: int = Field(foreign_key="composition.id", primary_key=True)


class ConcertGenre(SQLModel, table=True):
    concert_id: int = Field(foreign_key="concert.id", primary_key=True)
    genre_id: int = Field(foreign_key="genre.id", primary_key=True)
