from datetime import date, datetime

import pytest
from sqlmodel import Session

from figaro.db import make_test_engine
from figaro.domain.models import (Concert, FestivalDay, Hall, Program,
                                  RouteSheetItem)
from figaro.domain.routing.conflicts import Status
from figaro.services import auth, availability, sheets
from figaro.services.festival import create_festival


@pytest.fixture
def world():
    s = Session(make_test_engine())
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    u = auth.register(s, email="u@e.com", password="pw", consent=True)
    hall = Hall(festival_id=f.id, name="A", seats=100)
    s.add(hall)
    s.flush()
    day = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    s.add(day)
    s.flush()
    return s, f, u, hall, day


def _concert(s, f, hall, day, start, dur=45, sn=1, program_id=None):
    c = Concert(festival_id=f.id, show_num=sn, crm_show_id=sn, title=f"K{sn}", hall_id=hall.id,
                festival_day_id=day.id, starts_at=start, duration_min=dur, capacity=50,
                program_id=program_id)
    s.add(c)
    s.flush()
    return c


def _add_item(s, sheet, c, pos=0):
    s.add(RouteSheetItem(route_sheet_id=sheet.id, concert_id=c.id, position=pos))
    s.flush()


def test_add_overlap_rejected(world):
    s, f, u, hall, day = world
    sheet = sheets.create_empty(s, u.id, f.id)
    c1 = _concert(s, f, hall, day, datetime(2026, 7, 1, 12, 0), dur=60, sn=1)
    _add_item(s, sheet, c1)
    c2 = _concert(s, f, hall, day, datetime(2026, 7, 1, 12, 30), dur=60, sn=2)
    res = sheets.add_concert(s, sheet, c2.id)
    assert not res.added and res.status == Status.OVERLAP


def test_repeat_flag(world):
    s, f, u, hall, day = world
    sheet = sheets.create_empty(s, u.id, f.id)
    prog = Program(festival_id=f.id, signature="P")
    s.add(prog)
    s.flush()
    c1 = _concert(s, f, hall, day, datetime(2026, 7, 1, 13, 0), sn=1, program_id=prog.id)
    _add_item(s, sheet, c1)
    c2 = _concert(s, f, hall, day, datetime(2026, 7, 1, 15, 0), sn=2, program_id=prog.id)
    res = sheets.add_concert(s, sheet, c2.id)
    assert res.added and res.is_repeat


def test_soldout_rejected_with_alternative(world):
    s, f, u, hall, day = world
    sheet = sheets.create_empty(s, u.id, f.id)
    c1 = _concert(s, f, hall, day, datetime(2026, 7, 1, 13, 0), sn=1)
    _concert(s, f, hall, day, datetime(2026, 7, 1, 15, 0), sn=2)  # альтернатива
    availability.set_on_sale(s, c1.id, False)
    res = sheets.add_concert(s, sheet, c1.id)
    assert not res.added and "распродан" in res.reason and res.alternative_id is not None


def test_suggestions_fit_and_exclude_chosen(world):
    s, f, u, hall, day = world
    sheet = sheets.create_empty(s, u.id, f.id)
    a = _concert(s, f, hall, day, datetime(2026, 7, 1, 10, 0), dur=50, sn=1)
    b = _concert(s, f, hall, day, datetime(2026, 7, 1, 13, 0), dur=50, sn=2)
    _add_item(s, sheet, a, 0)
    _add_item(s, sheet, b, 1)
    fit = _concert(s, f, hall, day, datetime(2026, 7, 1, 11, 30), dur=45, sn=3)
    _concert(s, f, hall, day, datetime(2026, 7, 1, 10, 30), dur=45, sn=4)  # накладка
    sug = sheets.suggest_additions(s, sheet)
    ids = {x.concert_id for x in sug}
    assert fit.id in ids
    assert a.id not in ids and b.id not in ids
