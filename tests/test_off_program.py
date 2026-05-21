from datetime import date, datetime
from pathlib import Path

import pytest
from sqlmodel import Session, select

from figaro.db import make_test_engine
from figaro.domain.models import (Concert, FestivalDay, Hall, OffProgram,
                                  RouteSheetItem)
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services import auth, sheets
from figaro.services.festival import create_festival

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def session():
    engine = make_test_engine()
    with Session(engine) as s:
        yield s


def _fest(s):
    return create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                          starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))


def test_import_offprogram_scoped_and_idempotent(session):
    f = _fest(session)
    src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        off_program=[
            S.OffProgramRow(external_num=1, title="Лекция", hall_name="A",
                            starts_at=datetime(2026, 7, 1, 11, 30), duration_min=45, recommend=True),
            S.OffProgramRow(external_num=2, title="Выставка", hall_name="A",
                            starts_at=datetime(2026, 7, 1, 16, 0), duration_min=60, recommend=False),
        ])
    import_catalog(session, f.id, src)
    import_catalog(session, f.id, src)  # повторно — без дублей
    ops = session.exec(select(OffProgram).where(OffProgram.festival_id == f.id)).all()
    assert len(ops) == 2
    assert all(op.festival_id == f.id for op in ops)
    assert {op.external_num: op.is_recommended for op in ops} == {1: True, 2: False}
    lec = next(op for op in ops if op.external_num == 1)
    assert lec.hall_id is not None and lec.starts_at == datetime(2026, 7, 1, 11, 30)


def test_suggest_off_program_fits_gap_and_ranks_recommended(session):
    f = _fest(session)
    u = auth.register(session, email="u@e.com", password="pw", consent=True)
    hall = Hall(festival_id=f.id, name="A", seats=100)
    session.add(hall)
    session.flush()
    day = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    session.add(day)
    session.flush()
    sheet = sheets.create_empty(session, u.id, f.id)
    for i, (start, dur) in enumerate([(datetime(2026, 7, 1, 10, 0), 50),
                                      (datetime(2026, 7, 1, 13, 0), 50)]):
        c = Concert(festival_id=f.id, show_num=i + 1, crm_show_id=i + 1, title=f"K{i}",
                    hall_id=hall.id, festival_day_id=day.id, starts_at=start,
                    duration_min=dur, capacity=50)
        session.add(c)
        session.flush()
        session.add(RouteSheetItem(route_sheet_id=sheet.id, concert_id=c.id, position=i))
    session.flush()
    # помещается в щель 10:50–13:00; рекомендованное и обычное + накладка
    session.add(OffProgram(festival_id=f.id, external_num=10, title="Обычное", hall_id=hall.id,
                           starts_at=datetime(2026, 7, 1, 11, 30), duration_min=30, is_recommended=False))
    session.add(OffProgram(festival_id=f.id, external_num=11, title="Топ", hall_id=hall.id,
                           starts_at=datetime(2026, 7, 1, 12, 10), duration_min=30, is_recommended=True))
    session.add(OffProgram(festival_id=f.id, external_num=12, title="Накладка", hall_id=hall.id,
                           starts_at=datetime(2026, 7, 1, 10, 30), duration_min=45, is_recommended=False))
    session.flush()
    sug = sheets.suggest_off_program(session, sheet)
    titles = [s.title for s in sug]
    assert "Обычное" in titles and "Топ" in titles
    assert "Накладка" not in titles  # пересекается с первым концертом
    assert titles.index("Топ") < titles.index("Обычное")  # рекомендованные выше


@pytest.mark.skipif(not (DATA_DIR / "Offprogram-good.xlsx").exists(),
                    reason="нет реальной выгрузки офф-программы")
def test_offprogram_from_real_excel():
    rows = S.offprogram_from_excel(str(DATA_DIR))
    assert rows, "выгрузка офф-программы пуста"
    assert all(isinstance(r, S.OffProgramRow) for r in rows)
    assert all(r.external_num is not None and r.title for r in rows)
    # длительность парсится в минуты, где задана
    assert all(r.duration_min is None or r.duration_min >= 0 for r in rows)
