"""Наличие билетов — состояние (этап 4). Движок curve/replay/snapshots — этап 5.

До этапа 5 наличие — простой флаг (по умолчанию «в продаже» = шов pass-through).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from sqlmodel import Session, select

from figaro.domain.models import Concert, ConcertAvailability


def is_on_sale(session: Session, concert_id: int) -> bool:
    av = session.get(ConcertAvailability, concert_id)
    return True if av is None else av.is_on_sale


def set_on_sale(session: Session, concert_id: int, on_sale: bool,
                tickets_left: Optional[int] = None, source: str = "crm_import") -> None:
    av = session.get(ConcertAvailability, concert_id)
    if av is None:
        av = ConcertAvailability(concert_id=concert_id, is_on_sale=on_sale,
                                 tickets_left=tickets_left, source=source)
    else:
        av.is_on_sale = on_sale
        av.tickets_left = tickets_left
        av.source = source
    session.add(av)
    session.flush()


def find_alternative(session: Session, festival_id: int, concert: Concert) -> Optional[Concert]:
    """Простая альтернатива взамен распроданного: ближайший по времени доступный
    концерт того же дня (предпочтительно того же жанра). «Умная» — зона роста."""
    candidates = session.exec(select(Concert).where(
        Concert.festival_id == festival_id,
        Concert.festival_day_id == concert.festival_day_id,
        Concert.id != concert.id)).all()
    candidates = [c for c in candidates if is_on_sale(session, c.id)]
    if not candidates:
        return None
    candidates.sort(key=lambda c: abs((c.starts_at - concert.starts_at)))
    return candidates[0]
