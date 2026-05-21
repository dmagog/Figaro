from datetime import date, datetime

import pytest
from sqlmodel import Session

from figaro.db import make_test_engine
from figaro.domain.models import (Archetype, AvailabilitySnapshot, Concert,
                                  DayRoute, FestivalDay, Hall, Purchase)
from figaro.services import analytics
from figaro.services.festival import create_festival


@pytest.fixture
def world():
    s = Session(make_test_engine())
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    hall = Hall(festival_id=f.id, name="A", seats=100)
    s.add(hall)
    s.flush()
    day = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    s.add(day)
    s.flush()
    cs = []
    for i in range(3):
        c = Concert(festival_id=f.id, show_num=i + 1, crm_show_id=i + 1, title=f"K{i}",
                    hall_id=hall.id, festival_day_id=day.id,
                    starts_at=datetime(2026, 7, 1, 10 + i, 0), duration_min=45, capacity=50)
        s.add(c)
        cs.append(c)
    s.flush()
    arch = Archetype(festival_id=f.id, key="comfort", title="Комфортный")
    s.add(arch)
    s.flush()
    for cc in (2, 3):
        s.add(DayRoute(festival_id=f.id, festival_day_id=day.id, archetype_id=arch.id,
                       concerts_count=cc, comfort_score=0.5, diversity_score=0.5))
    s.commit()
    return s, f, cs


def test_overview_counts(world):
    s, f, cs = world
    ov = analytics.festival_overview(s, f.id)
    assert ov["concerts"] == 3 and ov["halls"] == 1
    assert ov["day_routes"] == 2 and ov["archetypes"] == 1
    assert ov["on_sale"] == 3 and ov["sold_out"] == 0  # шов: по умолчанию в продаже


def test_archetype_supply(world):
    s, f, _ = world
    supply = analytics.archetype_supply(s, f.id)
    assert len(supply) == 1
    assert supply[0]["title"] == "Комфортный" and supply[0]["routes"] == 2


def test_availability_timeline_groups_by_time(world):
    s, f, cs = world
    t1, t2 = datetime(2026, 6, 10), datetime(2026, 6, 20)
    s.add(AvailabilitySnapshot(concert_id=cs[0].id, at=t1, tickets_left=10, is_on_sale=True, source="sim_curve"))
    s.add(AvailabilitySnapshot(concert_id=cs[1].id, at=t1, tickets_left=0, is_on_sale=False, source="sim_curve"))
    s.add(AvailabilitySnapshot(concert_id=cs[0].id, at=t2, tickets_left=5, is_on_sale=True, source="sim_curve"))
    s.commit()
    tl = analytics.availability_timeline(s, f.id)
    assert [row["at"] for row in tl] == [t1, t2]
    assert tl[0] == {"at": t1, "tickets_left": 10, "sold_out": 1, "on_sale": 1}
    assert tl[1]["tickets_left"] == 5 and tl[1]["on_sale"] == 1


def test_customer_counts_pseudonymous(world):
    s, f, cs = world
    s.add(Purchase(festival_id=f.id, external_op_id=1, customer_external_id="x1",
                   concert_id=cs[0].id, purchased_at=datetime(2026, 6, 10)))
    s.add(Purchase(festival_id=f.id, external_op_id=2, customer_external_id="x1",
                   concert_id=cs[1].id, purchased_at=datetime(2026, 6, 11)))
    s.add(Purchase(festival_id=f.id, external_op_id=3, customer_external_id="x2",
                   concert_id=cs[0].id, purchased_at=datetime(2026, 6, 12)))
    s.commit()
    agg = analytics.customer_purchase_counts(s, f.id)
    assert agg["customers"] == 2 and agg["purchases"] == 3
    assert agg["top"][0] == {"customer": "x1", "purchases": 2}
