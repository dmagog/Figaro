"""Общие тест-хелперы для step-модулей этапа 4 (не содержит шагов)."""
from datetime import date, datetime, timedelta

from sqlmodel import select

from figaro.domain.models import (Author, Composition, Concert,
                                  ConcertComposition, ConcertGenre, FestivalDay,
                                  Genre, Hall, HallTransition, Program,
                                  RouteSheet, RouteSheetItem)
from figaro.importing.seed import _get_or_create
from figaro.services.festival import create_festival

DAY = date(2026, 7, 1)


def ensure_festival(context):
    if getattr(context, "festival", None) is None:
        context.festival = create_festival(context.session, name="2026", year=2026,
                                           sales_start_on=date(2026, 6, 1),
                                           starts_on=DAY, ends_on=date(2026, 7, 3))
    return context.festival


def hall(context, name, lat=None, lon=None):
    h = _get_or_create(context.session, Hall, festival_id=context.festival.id, name=name)
    h.seats = 100
    if lat is not None:
        h.lat, h.lon = lat, lon
    context.session.add(h)
    context.session.flush()
    return h


def transition(context, a, b, minutes):
    ha, hb = hall(context, a), hall(context, b)
    fid = context.festival.id
    for x, y in ((ha.id, hb.id), (hb.id, ha.id)):
        ex = context.session.exec(select(HallTransition).where(
            HallTransition.festival_id == fid, HallTransition.from_hall_id == x,
            HallTransition.to_hall_id == y)).first()
        if ex:
            ex.minutes = minutes
            context.session.add(ex)
        else:
            context.session.add(HallTransition(festival_id=fid, from_hall_id=x,
                                               to_hall_id=y, minutes=minutes))
    context.session.flush()


def program(context, sig):
    return _get_or_create(context.session, Program, festival_id=context.festival.id, signature=sig)


def at(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(DAY.year, DAY.month, DAY.day, h, m)


def concert(context, hall_name, start, dur=45, program_id=None, genre=None):
    fid = context.festival.id
    h = hall(context, hall_name)
    day = _get_or_create(context.session, FestivalDay, festival_id=fid, day=start.date())
    context._sn = getattr(context, "_sn", 1000) + 1  # выше show_num из Background-импорта
    c = Concert(festival_id=fid, show_num=context._sn, crm_show_id=context._sn,
                title=f"K{context._sn}", hall_id=h.id, festival_day_id=day.id,
                starts_at=start, duration_min=dur, capacity=50, program_id=program_id)
    context.session.add(c)
    context.session.flush()
    if genre:
        g = _get_or_create(context.session, Genre, festival_id=fid, name=genre)
        context.session.add(ConcertGenre(concert_id=c.id, genre_id=g.id))
        context.session.flush()
    return c


def attach_author(context, concert_obj, author_name):
    fid = context.festival.id
    a = _get_or_create(context.session, Author, festival_id=fid, name=author_name)
    comp = _get_or_create(context.session, Composition, festival_id=fid,
                          author_id=a.id, title=f"{author_name}-piece")
    context.session.add(ConcertComposition(concert_id=concert_obj.id, composition_id=comp.id))
    context.session.flush()


def empty_sheet(context):
    if getattr(context, "sheet", None) is None:
        s = RouteSheet(user_id=context.actor.id, festival_id=context.festival.id, title="Лист")
        context.session.add(s)
        context.session.flush()
        context.sheet = s
    return context.sheet


def add_item(context, concert_obj):
    sheet = empty_sheet(context)
    n = len(context.session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == sheet.id)).all())
    context.session.add(RouteSheetItem(route_sheet_id=sheet.id, concert_id=concert_obj.id, position=n))
    context.session.flush()
