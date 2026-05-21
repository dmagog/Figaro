from datetime import date, datetime

import pytest
from sqlmodel import Session, select

from figaro.db import make_test_engine
from figaro.domain.models import Concert, Program
from figaro.importing import source as S
from figaro.importing.dates import parse_datetime
from figaro.importing.seed import import_catalog
from figaro.services.festival import create_festival


@pytest.fixture
def session():
    engine = make_test_engine()
    with Session(engine) as s:
        yield s


def _fest(s):
    return create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                          starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))


def test_import_idempotent(session):
    f = _fest(session)
    src = S.CatalogSource(halls=[S.HallRow("A", seats=100)],
                          concerts=[S.ConcertRow(1, 42, "K", "A", datetime(2026, 7, 1, 13, 0), 45)])
    import_catalog(session, f.id, src)
    ids1 = [c.id for c in session.exec(select(Concert)).all()]
    import_catalog(session, f.id, src)
    ids2 = [c.id for c in session.exec(select(Concert)).all()]
    assert len(ids2) == 1 and ids1 == ids2


def test_program_signature_same(session):
    f = _fest(session)
    src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 11, "K1", "A", datetime(2026, 7, 1, 13, 0), 45),
                  S.ConcertRow(2, 12, "K2", "A", datetime(2026, 7, 1, 15, 0), 45)],
        compositions=[S.CompositionRow(1, "Бах", "Ария"), S.CompositionRow(2, "Бах", "Ария")])
    import_catalog(session, f.id, src)
    progs = session.exec(select(Program)).all()
    cs = session.exec(select(Concert)).all()
    assert len(progs) == 1 and len({c.program_id for c in cs}) == 1


def test_capacity_fallback(session):
    f = _fest(session)
    src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 11, "K1", "A", datetime(2026, 7, 1, 13, 0), 45, capacity=60),
                  S.ConcertRow(2, 12, "K2", "A", datetime(2026, 7, 1, 15, 0), 45, capacity=None)])
    import_catalog(session, f.id, src)
    by = {c.show_num: c for c in session.exec(select(Concert)).all()}
    assert by[1].capacity == 60 and by[2].capacity == 100


def test_parse_dates():
    assert parse_datetime("2026-06-21 11:00:00").year == 2026
    assert parse_datetime(46000).year >= 2000
    with pytest.raises(ValueError):
        parse_datetime("1970-01-01 05:00:00")
