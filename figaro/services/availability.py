"""Наличие билетов — состояние (этап 4). Движок curve/replay/snapshots — этап 5.

До этапа 5 наличие — простой флаг (по умолчанию «в продаже» = шов pass-through).
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from figaro.domain.models import (Artist, AvailabilitySnapshot, Concert,
                                  ConcertArtist, ConcertAvailability, DayRoute,
                                  DayRouteConcert, Festival, Purchase, SimState)
from figaro.services import cache


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


# ============ движок наличия (этап 5) ============
def _strip(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def get_sim_state(session: Session, festival_id: int) -> SimState:
    st = session.get(SimState, festival_id)
    if st is None:
        st = SimState(festival_id=festival_id)
        session.add(st)
        session.flush()
    return st


def set_mode(session: Session, festival_id: int, mode: str, seed: Optional[int] = None) -> SimState:
    st = get_sim_state(session, festival_id)
    st.availability_mode = mode
    if seed is not None:
        st.seed = seed
    session.add(st)
    session.flush()
    return st


def _popularity(session: Session, concert_id: int) -> float:
    rows = session.exec(select(Artist.is_special).where(
        Artist.id == ConcertArtist.artist_id, ConcertArtist.concert_id == concert_id)).all()
    return 1.0 if any(rows) else 0.0


def _curve_left(capacity: int, f: float, popularity: float, seed: int, concert_id: int) -> int:
    alpha = 0.5 if popularity >= 0.5 else 1.6  # популярные распродаются раньше
    sold = f ** alpha
    h = int(hashlib.md5(f"{concert_id}:{seed}".encode()).hexdigest(), 16) % 11
    sold = min(1.0, max(0.0, sold + ((h - 5) / 100.0) * f))  # детерминированный шум
    return max(0, capacity - round(capacity * sold))


def recompute(session: Session, festival_id: int, now: datetime,
              mode: Optional[str] = None, seed: Optional[int] = None) -> None:
    fest = session.get(Festival, festival_id)
    state = get_sim_state(session, festival_id)
    mode = mode or state.availability_mode
    seed = seed if seed is not None else state.seed
    now = _strip(now)
    sales_start = datetime(fest.sales_start_on.year, fest.sales_start_on.month, fest.sales_start_on.day)

    for c in session.exec(select(Concert).where(Concert.festival_id == festival_id)).all():
        cap = c.capacity or 0
        if mode == "sim_replay":
            sold = sum(1 for p in session.exec(select(Purchase).where(
                Purchase.concert_id == c.id)).all() if _strip(p.purchased_at) <= now)
            left = max(0, cap - sold)
        elif mode == "sim_curve":
            cstart = _strip(c.starts_at)
            total = (cstart - sales_start).total_seconds()
            f = 0.0 if total <= 0 else min(1.0, max(0.0, (now - sales_start).total_seconds() / total))
            left = _curve_left(cap, f, _popularity(session, c.id), seed, c.id)
        else:  # crm_import — обновляется файловым импортом (этап 7), здесь не трогаем
            continue
        on_sale = left > 0
        set_on_sale(session, c.id, on_sale, tickets_left=left, source=mode)
        session.add(AvailabilitySnapshot(concert_id=c.id, at=now, tickets_left=left,
                                         is_on_sale=on_sale, source=mode))
    session.flush()
    cache.invalidate(festival_id)  # AvailabilityChanged → инвалидация кэша маршрутов


def reset_to_sales_start(session: Session, festival_id: int) -> None:
    for c in session.exec(select(Concert).where(Concert.festival_id == festival_id)).all():
        set_on_sale(session, c.id, True, tickets_left=c.capacity, source="reset")
    cache.invalidate(festival_id)


def tick(session: Session, festival_id: int, clock, mode: Optional[str] = None,
         seed: Optional[int] = None) -> None:
    recompute(session, festival_id, clock.now(), mode, seed)


def route_available(session: Session, day_route_id: int) -> bool:
    cids = [l.concert_id for l in session.exec(select(DayRouteConcert).where(
        DayRouteConcert.day_route_id == day_route_id)).all()]
    return all(is_on_sale(session, cid) for cid in cids)


def available_day_routes(session: Session, festival_id: int) -> List[DayRoute]:
    return [dr for dr in session.exec(select(DayRoute).where(
        DayRoute.festival_id == festival_id)).all() if route_available(session, dr.id)]
