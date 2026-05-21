"""Маршрутный лист: создание (из маршрута / с нуля), добавление/удаление, закрепление,
подсказки дополнения (этап 4, docs/01, docs/03#подсказки-дополнения)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional

from sqlmodel import Session, select

from figaro.batch.precompute import build_resolver
from figaro.domain.models import (Concert, DayRouteConcert, OffProgram,
                                  RouteSheet, RouteSheetItem)
from figaro.domain.routing.conflicts import (PASSABLE, Status, TransitionConfig,
                                             evaluate)
from figaro.services import availability
from figaro.services.recommend import WeightProfile


@dataclass
class AddResult:
    added: bool
    status: Optional[Status] = None
    is_repeat: bool = False
    reason: Optional[str] = None
    alternative_id: Optional[int] = None


@dataclass
class Suggestion:
    concert_id: int
    after_id: Optional[int]
    before_id: Optional[int]
    transition_minutes: int
    is_repeat: bool
    score: float


def _items(session, sheet):
    return session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == sheet.id)).all()


def _concerts_in(session, sheet):
    cs = [session.get(Concert, it.concert_id) for it in _items(session, sheet)]
    return sorted(cs, key=lambda c: c.starts_at)


def _end(c: Concert):
    return c.starts_at + timedelta(minutes=c.duration_min)


def create_empty(session, user_id, festival_id, title=None) -> RouteSheet:
    s = RouteSheet(user_id=user_id, festival_id=festival_id, title=title, source="manual")
    session.add(s)
    session.flush()
    return s


def create_from_route(session, user_id, festival_id, day_route_id, title=None) -> RouteSheet:
    s = RouteSheet(user_id=user_id, festival_id=festival_id, title=title, source="from_archetype")
    session.add(s)
    session.flush()
    links = session.exec(select(DayRouteConcert).where(
        DayRouteConcert.day_route_id == day_route_id).order_by(DayRouteConcert.position)).all()
    for link in links:
        session.add(RouteSheetItem(route_sheet_id=s.id, concert_id=link.concert_id,
                                   position=link.position))
    session.flush()
    return s


def _status_between(a: Concert, b: Concert, resolver, cfg) -> Status:
    """Статус перехода между двумя концертами в порядке времени."""
    first, second = (a, b) if a.starts_at <= b.starts_at else (b, a)
    walk = resolver.walk(first.hall_id, second.hall_id)
    return evaluate(_end(first), second.starts_at, first.hall_id, second.hall_id, walk, cfg)


def chain_with_transitions(session, sheet):
    """Концерты листа по времени + переход с предыдущим: (статус, минуты ходьбы, окно между концертами).

    «Окно» (gap) = минуты от конца предыдущего концерта до начала следующего —
    содержательнее «голого» времени перехода (видно запас/нехватку времени)."""
    resolver = build_resolver(session, sheet.festival_id)
    cfg = TransitionConfig()
    out, prev = [], None
    for c in _concerts_in(session, sheet):
        trans = None
        if prev is not None:
            status = _status_between(prev, c, resolver, cfg)
            walk = resolver.walk(prev.hall_id, c.hall_id)
            gap = int((c.starts_at - _end(prev)).total_seconds() // 60)
            trans = (status, walk, gap)
        out.append((c, trans))
        prev = c
    return out


def add_concert(session: Session, sheet: RouteSheet, concert_id: int) -> AddResult:
    fid = sheet.festival_id
    concert = session.get(Concert, concert_id)
    if not availability.is_on_sale(session, concert_id):
        alt = availability.find_alternative(session, fid, concert)
        return AddResult(added=False, reason="концерт распродан",
                         alternative_id=(alt.id if alt else None))

    resolver = build_resolver(session, fid)
    cfg = TransitionConfig()
    existing = _concerts_in(session, sheet)
    is_repeat = False
    for ex in existing:
        if concert.program_id is not None and ex.program_id == concert.program_id and ex.id != concert.id:
            is_repeat = True
        if _status_between(ex, concert, resolver, cfg) == Status.OVERLAP:
            return AddResult(added=False, status=Status.OVERLAP, reason="накладка по времени")

    pos = len(existing)
    session.add(RouteSheetItem(route_sheet_id=sheet.id, concert_id=concert_id, position=pos))
    session.flush()

    # статус перехода с ближайшим по времени соседом (для отображения)
    chain = sorted(existing + [concert], key=lambda c: c.starts_at)
    idx = chain.index(concert)
    neighbor = chain[idx - 1] if idx > 0 else (chain[idx + 1] if len(chain) > 1 else None)
    status = _status_between(neighbor, concert, resolver, cfg) if neighbor else None
    return AddResult(added=True, status=status, is_repeat=is_repeat)


def remove_concert(session, sheet, concert_id) -> None:
    for it in _items(session, sheet):
        if it.concert_id == concert_id:
            session.delete(it)
    session.flush()


def set_pin(session, sheet, concert_id, pinned=True) -> None:
    for it in _items(session, sheet):
        if it.concert_id == concert_id:
            it.is_pinned = pinned
            session.add(it)
    session.flush()


def proposed_replacements(session, sheet) -> List[int]:
    """Замены предлагаем только для НЕ закреплённых концертов, ставших недоступными."""
    out = []
    for it in _items(session, sheet):
        if it.is_pinned:
            continue
        if not availability.is_on_sale(session, it.concert_id):
            out.append(it.concert_id)
    return out


def _fits_gap(cand: Concert, chain: List[Concert], resolver, cfg):
    """Возвращает (after_id, before_id, transition_minutes) если кандидат помещается в щель."""
    def ok(a, b):
        return _status_between(a, b, resolver, cfg) in PASSABLE

    if not chain:
        return (None, None, 0)
    # перед первым
    if _end(cand) <= chain[0].starts_at and ok(cand, chain[0]):
        return (None, chain[0].id, resolver.walk(cand.hall_id, chain[0].hall_id) or 0)
    # после последнего
    if chain[-1] is not None and _end(chain[-1]) <= cand.starts_at and ok(chain[-1], cand):
        return (chain[-1].id, None, resolver.walk(chain[-1].hall_id, cand.hall_id) or 0)
    # между соседями
    for a, b in zip(chain, chain[1:]):
        if _end(a) <= cand.starts_at and _end(cand) <= b.starts_at and ok(a, cand) and ok(cand, b):
            return (a.id, b.id, resolver.walk(a.hall_id, cand.hall_id) or 0)
    return None


def suggest_additions(session: Session, sheet: RouteSheet,
                      prof: Optional[WeightProfile] = None) -> List[Suggestion]:
    fid = sheet.festival_id
    resolver = build_resolver(session, fid)
    cfg = TransitionConfig()
    chain = _concerts_in(session, sheet)
    chosen = {c.id for c in chain}
    chosen_programs = {c.program_id for c in chain if c.program_id is not None}

    out = []
    for c in session.exec(select(Concert).where(Concert.festival_id == fid)).all():
        if c.id in chosen or not availability.is_on_sale(session, c.id):
            continue
        fit = _fits_gap(c, chain, resolver, cfg)
        if fit is None:
            continue
        after_id, before_id, trans = fit
        is_repeat = c.program_id is not None and c.program_id in chosen_programs
        score = _favorites_bonus(session, c, prof)
        out.append(Suggestion(concert_id=c.id, after_id=after_id, before_id=before_id,
                              transition_minutes=trans, is_repeat=is_repeat, score=score))
    out.sort(key=lambda s: s.score, reverse=True)
    return out


@dataclass
class OffProgramSuggestion:
    off_program_id: int
    title: str
    is_recommended: bool
    after_id: Optional[int]
    before_id: Optional[int]
    transition_minutes: int


def suggest_off_program(session: Session, sheet: RouteSheet) -> List[OffProgramSuggestion]:
    """Внепрограммные события, помещающиеся в щели маршрута. Рекомендованные — выше."""
    fid = sheet.festival_id
    resolver = build_resolver(session, fid)
    cfg = TransitionConfig()
    chain = _concerts_in(session, sheet)
    out = []
    for op in session.exec(select(OffProgram).where(OffProgram.festival_id == fid)).all():
        if op.starts_at is None or op.duration_min is None or op.hall_id is None:
            continue
        fit = _fits_gap(op, chain, resolver, cfg)  # у OffProgram есть hall_id/starts_at/duration_min
        if fit is None:
            continue
        after_id, before_id, trans = fit
        out.append(OffProgramSuggestion(off_program_id=op.id, title=op.title,
                                        is_recommended=op.is_recommended, after_id=after_id,
                                        before_id=before_id, transition_minutes=trans))
    out.sort(key=lambda s: (not s.is_recommended,))  # рекомендованные выше
    return out


def _favorites_bonus(session, concert: Concert, prof: Optional[WeightProfile]) -> float:
    if prof is None:
        return 0.0
    from figaro.batch.precompute import _concert_lite
    lite = _concert_lite(session, concert)
    genres = {lite.genre} if lite.genre else set()
    overlap = len(set(lite.authors) & set(prof.fav_authors)) + len(genres & set(prof.fav_genres))
    return 0.5 * overlap
