"""Сервис фестиваля: создание (draft), активный фестиваль, скоуп-выборки.

Активация (draft→active с гейтом по предрасчёту) — этап 2; здесь только то,
что нужно этапу 1 (создание и скоуп по активному фестивалю).
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlmodel import Session, select

from figaro.domain.models import Concert, Festival


def create_festival(session: Session, *, name: str, year: int, sales_start_on: date,
                    starts_on: date, ends_on: date, timezone: str = "Europe/Moscow") -> Festival:
    fest = Festival(name=name, year=year, sales_start_on=sales_start_on,
                    starts_on=starts_on, ends_on=ends_on, timezone=timezone, status="draft")
    session.add(fest)
    session.flush()
    return fest


def get_active(session: Session) -> Optional[Festival]:
    return session.exec(select(Festival).where(Festival.status == "active")).first()


def activate(session: Session, festival_id: int) -> Festival:
    """Этап 2: гейт по предрасчёту добавится там. Здесь — базовый инвариант 'один активный'."""
    for f in session.exec(select(Festival).where(Festival.status == "active")).all():
        f.status = "archived"
        session.add(f)
    fest = session.get(Festival, festival_id)
    fest.status = "active"
    session.add(fest)
    session.flush()
    return fest


def concerts_for_active(session: Session) -> List[Concert]:
    """Публичная выборка ограничена активным фестивалём."""
    active = get_active(session)
    if active is None:
        return []
    return session.exec(select(Concert).where(Concert.festival_id == active.id)).all()
