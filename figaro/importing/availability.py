"""Импорт наличия из файла остатков (этап 7, продакшн-путь crm_import).

Обновляет только наличие (ConcertAvailability + снимок), каталог не трогает.
Позже тем же контрактом — pull по API CRM.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, Tuple

from sqlmodel import Session, select

from figaro.domain.models import AvailabilitySnapshot, Concert
from figaro.services import availability, cache


def import_availability(session: Session, festival_id: int,
                        rows: Iterable[Tuple[int, int]],
                        now: Optional[datetime] = None) -> int:
    """rows: (crm_show_id, tickets_left). Привязка к концерту по crm_show_id."""
    now = now or datetime.utcnow()
    now = now.replace(tzinfo=None) if now.tzinfo else now
    updated = 0
    for crm_show_id, tickets_left in rows:
        c = session.exec(select(Concert).where(
            Concert.festival_id == festival_id, Concert.crm_show_id == crm_show_id)).first()
        if c is None:
            continue
        on_sale = tickets_left > 0
        availability.set_on_sale(session, c.id, on_sale, tickets_left=tickets_left,
                                 source="crm_import")
        session.add(AvailabilitySnapshot(concert_id=c.id, at=now, tickets_left=tickets_left,
                                         is_on_sale=on_sale, source="crm_import"))
        updated += 1
    session.flush()
    cache.invalidate(festival_id)  # пересчёт доступных маршрутов
    return updated
