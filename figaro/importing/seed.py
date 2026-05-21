"""Импорт каталога фестиваля (этап 1). Идемпотентно, в рамках festival_id.

- связка каталога по `show_num`, покупки — по `crm_show_id`;
- capacity = из выгрузки, иначе вместимость зала;
- сигнатура программы из множества (автор, произведение);
- переходы между залами — в обе стороны;
- устойчивый парсинг дат покупок.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import List, Tuple

from sqlmodel import Session, select

from figaro.domain.models import (
    Artist, Author, Composition, Concert, ConcertArtist, ConcertComposition,
    ConcertGenre, FestivalDay, Genre, Hall, HallTransition, OffProgram, Program,
    Purchase,
)
from figaro.importing.dates import parse_datetime
from figaro.importing.source import CatalogSource


def _get_or_create(session: Session, Model, defaults=None, **keys):
    obj = session.exec(select(Model).filter_by(**keys)).first()
    if obj is not None:
        return obj
    obj = Model(**keys, **(defaults or {}))
    session.add(obj)
    session.flush()
    return obj


def _signature(pairs: List[Tuple[str, str]]) -> str:
    norm = sorted(f"{a.strip()}::{t.strip()}" for a, t in pairs)
    return hashlib.sha1("|".join(norm).encode("utf-8")).hexdigest()


def import_catalog(session: Session, festival_id: int, src: CatalogSource) -> None:
    fid = festival_id

    # 1. Залы
    hall_by_name = {}
    for h in src.halls:
        obj = _get_or_create(session, Hall, festival_id=fid, name=h.name)
        obj.address, obj.seats, obj.lat, obj.lon = h.address, h.seats or 0, h.lat, h.lon
        session.add(obj)
        hall_by_name[h.name] = obj
    session.flush()

    # 2. Переходы — обе стороны
    def ensure_transition(frm_id: int, to_id: int, minutes: int) -> None:
        ex = session.exec(select(HallTransition).where(
            HallTransition.festival_id == fid,
            HallTransition.from_hall_id == frm_id,
            HallTransition.to_hall_id == to_id)).first()
        if ex:
            ex.minutes = minutes
            session.add(ex)
        else:
            session.add(HallTransition(festival_id=fid, from_hall_id=frm_id,
                                       to_hall_id=to_id, minutes=minutes))

    for t in src.transitions:
        f, to = hall_by_name.get(t.from_name), hall_by_name.get(t.to_name)
        if f and to and f.id != to.id:
            ensure_transition(f.id, to.id, t.minutes)
            ensure_transition(to.id, f.id, t.minutes)
    session.flush()

    # 3. Авторы + произведения; накопить состав по show_num
    pieces_by_show, comp_ids_by_show = {}, {}
    for c in src.compositions:
        author = _get_or_create(session, Author, festival_id=fid, name=c.author.strip())
        comp = _get_or_create(session, Composition, festival_id=fid,
                              author_id=author.id, title=c.title.strip())
        pieces_by_show.setdefault(c.show_num, []).append((c.author, c.title))
        comp_ids_by_show.setdefault(c.show_num, []).append(comp.id)
    session.flush()

    # 4. Программы по сигнатуре
    program_id_by_show = {}
    for sn, pieces in pieces_by_show.items():
        prog = _get_or_create(session, Program, festival_id=fid, signature=_signature(pieces))
        program_id_by_show[sn] = prog.id

    # 5. Концерты
    concert_by_show = {}
    for c in src.concerts:
        hall = hall_by_name.get(c.hall_name)
        starts = parse_datetime(c.starts_at)
        day = _get_or_create(session, FestivalDay, festival_id=fid, day=starts.date())
        capacity = c.capacity if c.capacity is not None else (hall.seats if hall else 0)

        obj = session.exec(select(Concert).where(
            Concert.festival_id == fid, Concert.show_num == c.show_num)).first()
        if obj is None:
            obj = Concert(festival_id=fid, show_num=c.show_num, title=c.title,
                          hall_id=hall.id if hall else None, starts_at=starts,
                          duration_min=c.duration_min, capacity=capacity)
            session.add(obj)
        obj.crm_show_id = c.crm_show_id
        obj.title = c.title
        obj.hall_id = hall.id if hall else None
        obj.festival_day_id = day.id
        obj.starts_at = starts
        obj.duration_min = c.duration_min
        obj.price_kopecks = c.price_kopecks or 0
        obj.is_family_friendly = bool(c.is_family_friendly)
        obj.capacity = capacity
        obj.program_id = program_id_by_show.get(c.show_num)
        session.add(obj)
        session.flush()
        concert_by_show[c.show_num] = obj

        if c.genre:
            g = _get_or_create(session, Genre, festival_id=fid, name=c.genre.strip())
            if not session.exec(select(ConcertGenre).where(
                    ConcertGenre.concert_id == obj.id, ConcertGenre.genre_id == g.id)).first():
                session.add(ConcertGenre(concert_id=obj.id, genre_id=g.id))
        for comp_id in comp_ids_by_show.get(c.show_num, []):
            if not session.exec(select(ConcertComposition).where(
                    ConcertComposition.concert_id == obj.id,
                    ConcertComposition.composition_id == comp_id)).first():
                session.add(ConcertComposition(concert_id=obj.id, composition_id=comp_id))
    session.flush()

    # 6. Артисты + связь
    for a in src.artists:
        art = _get_or_create(session, Artist, festival_id=fid, name=a.name.strip())
        if a.is_special and not art.is_special:
            art.is_special = True
            session.add(art)
        concert = concert_by_show.get(a.show_num)
        if concert and not session.exec(select(ConcertArtist).where(
                ConcertArtist.concert_id == concert.id, ConcertArtist.artist_id == art.id)).first():
            session.add(ConcertArtist(concert_id=concert.id, artist_id=art.id))
    session.flush()

    # 7. Агрегаты дней фестиваля
    for day in session.exec(select(FestivalDay).where(FestivalDay.festival_id == fid)).all():
        concerts = session.exec(select(Concert).where(
            Concert.festival_id == fid, Concert.festival_day_id == day.id)).all()
        if concerts:
            day.first_concert_at = min(c.starts_at for c in concerts)
            day.last_concert_at = max(c.starts_at for c in concerts)
            day.last_concert_ends_at = max(c.starts_at + timedelta(minutes=c.duration_min) for c in concerts)
            day.concert_count = len(concerts)
            session.add(day)
    session.flush()

    # 8. Покупки — привязка по crm_show_id, устойчивые даты
    concert_by_crm = {c.crm_show_id: c for c in session.exec(
        select(Concert).where(Concert.festival_id == fid)).all() if c.crm_show_id is not None}
    for p in src.purchases:
        concert = concert_by_crm.get(p.crm_show_id)
        if not concert:
            continue
        purchased = parse_datetime(p.purchased_at_raw)
        obj = session.exec(select(Purchase).where(
            Purchase.festival_id == fid, Purchase.external_op_id == p.external_op_id)).first()
        if obj is None:
            obj = Purchase(festival_id=fid, external_op_id=p.external_op_id,
                           customer_external_id=str(p.customer_external_id),
                           concert_id=concert.id, purchased_at=purchased)
            session.add(obj)
        obj.customer_external_id = str(p.customer_external_id)
        obj.concert_id = concert.id
        obj.purchased_at = purchased
        obj.price_kopecks = p.price_kopecks or 0
        session.add(obj)
    session.flush()

    # 9. Офф-программа (внепрограммные события)
    for op in src.off_program:
        hall = hall_by_name.get(op.hall_name) if op.hall_name else None
        starts = parse_datetime(op.starts_at) if op.starts_at is not None else None
        obj = session.exec(select(OffProgram).where(
            OffProgram.festival_id == fid, OffProgram.external_num == op.external_num)).first()
        if obj is None:
            obj = OffProgram(festival_id=fid, external_num=op.external_num, title=op.title)
            session.add(obj)
        obj.title = op.title
        obj.description = op.description
        obj.starts_at = starts
        obj.duration_min = op.duration_min
        obj.hall_id = hall.id if hall else None
        obj.fmt = op.fmt
        obj.is_recommended = bool(op.recommend)
        obj.link = op.link
        session.add(obj)
    session.flush()
