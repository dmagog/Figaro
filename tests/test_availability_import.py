from datetime import date, datetime

import pytest
from sqlmodel import Session, select

from figaro.db import make_test_engine
from figaro.domain.models import (AvailabilitySnapshot, Concert,
                                  ConcertAvailability, FestivalDay, Hall)
from figaro.importing.availability import import_availability
from figaro.services import cache
from figaro.services.festival import create_festival


@pytest.fixture
def world():
    s = Session(make_test_engine())
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    hall = Hall(festival_id=f.id, name="A", seats=100)
    s.add(hall)
    s.flush()
    fd = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    s.add(fd)
    s.flush()
    c = Concert(festival_id=f.id, show_num=1, crm_show_id=501, title="K", hall_id=hall.id,
                festival_day_id=fd.id, starts_at=datetime(2026, 7, 1, 13), duration_min=45, capacity=50)
    s.add(c)
    s.flush()
    return s, f, c


def test_import_updates_and_invalidates(world):
    s, f, c = world
    cache.set(f.id, ["x"])
    n = import_availability(s, f.id, [(501, 0)], now=datetime(2026, 6, 30))
    assert n == 1
    av = s.get(ConcertAvailability, c.id)
    assert av.is_on_sale is False and av.source == "crm_import"
    assert cache.get(f.id) is None


def test_import_writes_snapshot(world):
    s, f, c = world
    import_availability(s, f.id, [(501, 7)], now=datetime(2026, 6, 30))
    snaps = s.exec(select(AvailabilitySnapshot).where(
        AvailabilitySnapshot.source == "crm_import")).all()
    assert snaps and snaps[0].tickets_left == 7
