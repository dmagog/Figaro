from datetime import date, datetime

import pytest
from sqlmodel import Session

from figaro.db import make_test_engine
from figaro.domain.models import (Artist, Concert, ConcertArtist,
                                  ConcertAvailability, DayRoute,
                                  DayRouteConcert, FestivalDay, Hall, Purchase)
from figaro.services import availability
from figaro.services.festival import create_festival


@pytest.fixture
def world():
    s = Session(make_test_engine())
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    hall = Hall(festival_id=f.id, name="A", seats=100)
    s.add(hall)
    s.flush()
    return s, f, hall


def _concert(s, f, hall, start, cap=50, sn=1, special=False):
    from sqlmodel import select
    fd = s.exec(select(FestivalDay).where(
        FestivalDay.festival_id == f.id, FestivalDay.day == start.date())).first()
    if fd is None:
        fd = FestivalDay(festival_id=f.id, day=start.date())
        s.add(fd)
        s.flush()
    c = Concert(festival_id=f.id, show_num=sn, crm_show_id=sn, title=f"K{sn}", hall_id=hall.id,
                festival_day_id=fd.id, starts_at=start, duration_min=45, capacity=cap)
    s.add(c)
    s.flush()
    if special:
        a = Artist(festival_id=f.id, name=f"Star{sn}", is_special=True)
        s.add(a)
        s.flush()
        s.add(ConcertArtist(concert_id=c.id, artist_id=a.id))
        s.flush()
    return c


def test_replay(world):
    s, f, hall = world
    c = _concert(s, f, hall, datetime(2026, 6, 25, 19), cap=5, sn=1)
    for i in range(3):
        s.add(Purchase(festival_id=f.id, external_op_id=i, customer_external_id=f"c{i}",
                       concert_id=c.id, purchased_at=datetime(2026, 6, 19)))
    s.flush()
    availability.recompute(s, f.id, datetime(2026, 6, 20), mode="sim_replay")
    assert s.get(ConcertAvailability, c.id).tickets_left == 2


def test_curve_reproducible(world):
    s, f, hall = world
    c = _concert(s, f, hall, datetime(2026, 6, 25, 19), sn=1)
    availability.recompute(s, f.id, datetime(2026, 6, 20), mode="sim_curve", seed=42)
    a = s.get(ConcertAvailability, c.id).tickets_left
    availability.recompute(s, f.id, datetime(2026, 6, 20), mode="sim_curve", seed=42)
    b = s.get(ConcertAvailability, c.id).tickets_left
    assert a == b


def test_curve_popular_sooner(world):
    s, f, hall = world
    head = _concert(s, f, hall, datetime(2026, 6, 25, 19), sn=1, special=True)
    norm = _concert(s, f, hall, datetime(2026, 6, 25, 19), sn=2, special=False)
    availability.recompute(s, f.id, datetime(2026, 6, 24), mode="sim_curve", seed=42)
    assert s.get(ConcertAvailability, head.id).tickets_left < s.get(ConcertAvailability, norm.id).tickets_left


def test_reset(world):
    s, f, hall = world
    c = _concert(s, f, hall, datetime(2026, 6, 25, 19), cap=50, sn=1)
    availability.set_on_sale(s, c.id, False, 0)
    availability.reset_to_sales_start(s, f.id)
    av = s.get(ConcertAvailability, c.id)
    assert av.is_on_sale and av.tickets_left == 50


def test_route_available(world):
    s, f, hall = world
    c = _concert(s, f, hall, datetime(2026, 7, 1, 13), sn=1)
    dr = DayRoute(festival_id=f.id, festival_day_id=c.festival_day_id, concerts_count=1)
    s.add(dr)
    s.flush()
    s.add(DayRouteConcert(day_route_id=dr.id, concert_id=c.id, position=0))
    s.flush()
    assert availability.route_available(s, dr.id)
    availability.set_on_sale(s, c.id, False, 0)
    assert not availability.route_available(s, dr.id)
