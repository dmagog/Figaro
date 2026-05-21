# language: ru
"""Шаги для catalog_import.feature (этап 1)."""
from datetime import date, datetime

from behave import given, then, when
from sqlmodel import select

from figaro.domain.models import (Concert, ConcertArtist, ConcertComposition,
                                  FestivalDay, Hall, HallTransition, Program, Purchase)
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services.festival import create_festival


def _fest(context):
    if context.festival is None:
        context.festival = create_festival(
            context.session, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
            starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    return context.festival


def _hall(context, name):
    return context.session.exec(select(Hall).where(
        Hall.festival_id == context.festival.id, Hall.name == name)).first()


def _do_import(context):
    import_catalog(context.session, _fest(context).id, context.src)


# --- идемпотентность ---
@given('выгрузка с концертом external_id "{ext}"')
def step_src_concert_ext(context, ext):
    sn = int(ext)
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(sn, sn, "K", "A", datetime(2026, 7, 1, 13, 0), 45)])


@when('импорт каталога выполняется дважды')
def step_import_twice(context):
    _do_import(context)
    context.first_ids = [c.id for c in context.session.exec(select(Concert)).all()]
    _do_import(context)


@then('в каталоге ровно один концерт с external_id "{ext}"')
def step_one_concert(context, ext):
    cs = context.session.exec(select(Concert).where(Concert.show_num == int(ext))).all()
    assert len(cs) == 1, len(cs)


@then('его внутренний id не меняется между запусками')
def step_id_stable(context):
    now = [c.id for c in context.session.exec(select(Concert)).all()]
    assert now == context.first_ids, (now, context.first_ids)


# --- сигнатура программы ---
@given('два концерта с одинаковым набором произведений и авторов')
def step_two_same_program(context):
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 11, "K1", "A", datetime(2026, 7, 1, 13, 0), 45),
                  S.ConcertRow(2, 12, "K2", "A", datetime(2026, 7, 1, 15, 0), 45)],
        compositions=[S.CompositionRow(1, "Бах", "Ария"), S.CompositionRow(1, "Шуман", "Арабески"),
                      S.CompositionRow(2, "Шуман", "Арабески"), S.CompositionRow(2, "Бах", "Ария")])


@when('импорт строит программы')
def step_build_programs(context):
    _do_import(context)


@then('оба концерта ссылаются на одну программу')
def step_same_program(context):
    cs = context.session.exec(select(Concert)).all()
    pids = {c.program_id for c in cs}
    assert len(cs) == 2 and len(pids) == 1 and None not in pids, pids


@then('эта программа имеет одну сигнатуру')
def step_one_signature(context):
    progs = context.session.exec(select(Program)).all()
    assert len(progs) == 1, len(progs)


# --- переходы обе стороны ---
@given('в матрице задано время перехода "{a}"->"{b}" = {m:d} минут')
def step_transition_src(context, a, b, m):
    context.src = S.CatalogSource(
        halls=[S.HallRow(a, seats=10), S.HallRow(b, seats=10)],
        transitions=[S.TransitionRow(a, b, m)])


@when('импорт загружает матрицу переходов')
def step_import_transitions(context):
    _do_import(context)


@then('доступно время перехода "{a}"->"{b}" = {m:d} минут')
def step_check_transition_minutes(context, a, b, m):
    ha, hb = _hall(context, a), _hall(context, b)
    tr = context.session.exec(select(HallTransition).where(
        HallTransition.from_hall_id == ha.id, HallTransition.to_hall_id == hb.id)).first()
    assert tr and tr.minutes == m


@then('доступно время перехода "{a}"->"{b}"')
def step_check_transition_exists(context, a, b):
    ha, hb = _hall(context, a), _hall(context, b)
    tr = context.session.exec(select(HallTransition).where(
        HallTransition.from_hall_id == ha.id, HallTransition.to_hall_id == hb.id)).first()
    assert tr is not None


# --- день + зал ---
@given('концерт с датой "{ts}" в зале "{hall}"')
def step_concert_day_src(context, ts, hall):
    dt = datetime.fromisoformat(ts)
    context.src = S.CatalogSource(
        halls=[S.HallRow(hall, seats=50)],
        concerts=[S.ConcertRow(1, 11, "K", hall, dt, 45)])


@when('импорт строит дни фестиваля')
def step_import_days(context):
    _do_import(context)


@then('концерт привязан к дню фестиваля "{d}"')
def step_concert_in_day(context, d):
    c = context.session.exec(select(Concert)).first()
    day = context.session.get(FestivalDay, c.festival_day_id)
    assert day.day == date.fromisoformat(d), day.day


@then('концерт привязан к залу "{hall}" по внутреннему id, а не по строке')
def step_concert_hall(context, hall):
    c = context.session.exec(select(Concert)).first()
    h = context.session.get(Hall, c.hall_id)
    assert h.name == hall and isinstance(c.hall_id, int)


# --- покупки с датой ---
@given('выгрузка покупок с датами покупки')
def step_purchases_src(context):
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 42, "K", "A", datetime(2026, 7, 1, 13, 0), 45)],
        purchases=[S.PurchaseRow(5001, "c1", 42, datetime(2026, 6, 20, 10, 0)),
                   S.PurchaseRow(5002, "c2", 42, "2026-06-21 11:00:00")])


@when('импорт загружает покупки')
def step_import_purchases(context):
    _do_import(context)


@then('у каждой покупки есть концерт и дата покупки')
def step_purchases_ok(context):
    ps = context.session.exec(select(Purchase)).all()
    assert ps and all(p.concert_id and p.purchased_at for p in ps)


@then('покупки доступны для режима наличия "sim_replay"')
def step_purchases_replay(context):
    ps = context.session.exec(select(Purchase)).all()
    assert all(p.purchased_at.year >= 2022 for p in ps)


# --- ShowNum vs ShowId ---
@given('в выгрузке концерт с "ShowNum" = {sn:d} и "ShowId" = {sid:d}')
def step_concert_ids(context, sn, sid):
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(sn, sid, "K", "A", datetime(2026, 7, 1, 13, 0), 45)],
        artists=[S.ArtistRow(sn, "Артист")],
        compositions=[S.CompositionRow(sn, "Бах", "Ария")])


@given('покупка ссылается на концерт по "ShowId" = {sid:d}')
def step_purchase_by_showid(context, sid):
    context.src.purchases.append(S.PurchaseRow(7001, "c1", sid, datetime(2026, 6, 20, 10, 0)))


@when('импорт связывает данные')
def step_import_link(context):
    _do_import(context)


@then('артисты и программа концерта подтянуты по "ShowNum" = {sn:d}')
def step_linked_by_shownum(context, sn):
    c = context.session.exec(select(Concert).where(Concert.show_num == sn)).first()
    arts = context.session.exec(select(ConcertArtist).where(ConcertArtist.concert_id == c.id)).all()
    comps = context.session.exec(select(ConcertComposition).where(ConcertComposition.concert_id == c.id)).all()
    assert arts and comps and c.program_id is not None


@then('покупка привязана к этому концерту по "crm_show_id" = {sid:d}')
def step_purchase_linked(context, sid):
    c = context.session.exec(select(Concert).where(Concert.crm_show_id == sid)).first()
    ps = context.session.exec(select(Purchase).where(Purchase.concert_id == c.id)).all()
    assert ps


# --- capacity ---
@given('концерт в зале с вместимостью {seats:d}')
def step_hall_capacity(context, seats):
    context.src = S.CatalogSource(halls=[S.HallRow("A", seats=seats)])


@when('у концерта в выгрузке указана своя вместимость {cap:d}')
def step_concert_capacity(context, cap):
    context.src.concerts.append(S.ConcertRow(1, 11, "K1", "A", datetime(2026, 7, 1, 13, 0), 45, capacity=cap))
    _do_import(context)


@then('capacity концерта = {cap:d}')
def step_check_capacity(context, cap):
    c = context.session.exec(select(Concert).where(Concert.show_num == 1)).first()
    assert c.capacity == cap, c.capacity


@when('у другого концерта вместимость в выгрузке не указана')
def step_concert_no_capacity(context):
    context.src.concerts.append(S.ConcertRow(2, 12, "K2", "A", datetime(2026, 7, 1, 15, 0), 45, capacity=None))
    _do_import(context)


@then('его capacity = вместимости зала = {seats:d}')
def step_check_capacity_hall(context, seats):
    c = context.session.exec(select(Concert).where(Concert.show_num == 2)).first()
    assert c.capacity == seats, c.capacity


# --- форматы дат ---
@given('в выгрузке даты покупок в разных форматах (datetime, строка, Excel-serial)')
def step_mixed_dates(context):
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 42, "K", "A", datetime(2026, 7, 1, 13, 0), 45)],
        purchases=[S.PurchaseRow(1, "c1", 42, datetime(2026, 6, 20, 10, 0)),
                   S.PurchaseRow(2, "c2", 42, "2026-06-21 11:00:00"),
                   S.PurchaseRow(3, "c3", 42, 46000)])  # Excel-serial → ~2025-12


@when('импорт парсит даты')
def step_parse_dates(context):
    _do_import(context)


@then('все `purchased_at` распознаны как корректные даты')
def step_dates_ok(context):
    ps = context.session.exec(select(Purchase)).all()
    assert len(ps) == 3 and all(isinstance(p.purchased_at, datetime) for p in ps)


@then('артефакты вида "1970-01-01" не попадают в данные')
def step_no_1970(context):
    ps = context.session.exec(select(Purchase)).all()
    assert all(p.purchased_at.year >= 2000 for p in ps)
