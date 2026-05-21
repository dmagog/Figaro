# language: ru
"""Шаги для festival_lifecycle.feature (этап 1: создание, скоуп, активный фестиваль)."""
from datetime import date, datetime

from behave import given, then, when
from sqlmodel import select

from figaro.domain.models import Concert, Hall, Program, Purchase
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services.festival import (activate, concerts_for_active,
                                      create_festival, get_active)


def _mini_source(show_num=1, crm=42, hall="A"):
    return S.CatalogSource(
        halls=[S.HallRow(name=hall, seats=100)],
        concerts=[S.ConcertRow(show_num=show_num, crm_show_id=crm, title="K", hall_name=hall,
                               starts_at=datetime(2026, 7, 1, 13, 0), duration_min=45,
                               genre="Камерные программы")],
        artists=[S.ArtistRow(show_num=show_num, name="Артист")],
        compositions=[S.CompositionRow(show_num=show_num, author="Бах", title="Ария")],
        purchases=[S.PurchaseRow(external_op_id=1000 + show_num, customer_external_id="c1",
                                 crm_show_id=crm, purchased_at_raw=datetime(2026, 6, 20, 10, 0))],
    )


def _new_festival(context, name, status="draft"):
    y = int(name)
    f = create_festival(context.session, name=name, year=y, sales_start_on=date(y, 6, 1),
                        starts_on=date(y, 7, 1), ends_on=date(y, 7, 3))
    if status == "active":
        activate(context.session, f.id)
    context.festivals[name] = f
    return f


@when('администратор создаёт фестиваль "{name}" с датами "{start}".."{end}"')
def step_create(context, name, start, end):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    context.festival = create_festival(context.session, name=name, year=s.year,
                                       sales_start_on=date(s.year, 6, 1), starts_on=s, ends_on=e)


@then('фестиваль создан в статусе "{status}"')
def step_status(context, status):
    assert context.festival.status == status, context.festival.status


@then('он не виден публичному сайту')
def step_not_public(context):
    assert get_active(context.session) is None


@given('фестиваль "{name}" в статусе "{status}"')
def step_given_festival(context, name, status):
    context.festival = _new_festival(context, name, status)


@when('администратор импортирует каталог в этот фестиваль')
def step_import(context):
    import_catalog(context.session, context.festival.id, _mini_source())


@then('все концерты, залы, программы и покупки имеют его "festival_id"')
def step_scoped(context):
    fid = context.festival.id
    for Model in (Concert, Hall, Program, Purchase):
        rows = context.session.exec(select(Model)).all()
        assert rows, f"нет строк {Model.__name__}"
        assert all(r.festival_id == fid for r in rows), Model.__name__


@then('данные других фестивалей не затронуты')
def step_no_other(context):
    fids = {c.festival_id for c in context.session.exec(select(Concert)).all()}
    assert fids == {context.festival.id}, fids


@given('фестивали "{a}" и "{b}"')
def step_two_fests(context, a, b):
    _new_festival(context, a)
    _new_festival(context, b)


@when('в каждый импортируется концерт с "show_num" = {n:d}')
def step_import_each(context, n):
    for i, (name, f) in enumerate(context.festivals.items()):
        import_catalog(context.session, f.id, _mini_source(show_num=n, crm=100 + i))


@then('оба концерта существуют независимо')
def step_both_exist(context):
    cs = context.session.exec(select(Concert)).all()
    assert len(cs) == 2 and len({c.festival_id for c in cs}) == 2


@then('их связь с CRM идёт по "crm_show_id", а не по "show_num"')
def step_crm(context):
    cs = context.session.exec(select(Concert)).all()
    assert all(c.crm_show_id is not None for c in cs)
    assert len({c.crm_show_id for c in cs}) == 2  # разные crm при одинаковом show_num


@given('активен фестиваль "{name}"')
def step_active(context, name):
    f = _new_festival(context, name, status="active")
    import_catalog(context.session, f.id, _mini_source(show_num=1, crm=42))


@given('существует архивный фестиваль "{name}"')
def step_archived(context, name):
    f = _new_festival(context, name)
    import_catalog(context.session, f.id, _mini_source(show_num=1, crm=99))
    f.status = "archived"
    context.session.add(f)
    context.session.flush()


@when('выполняется публичная выборка данных')
def step_public_query(context):
    context.public = concerts_for_active(context.session)


@then('возвращаются только данные активного фестиваля "{name}"')
def step_only_active(context, name):
    fid = context.festivals[name].id
    assert context.public and all(c.festival_id == fid for c in context.public)


@then('данные фестиваля "{name}" в выборку не попадают')
def step_not_in(context, name):
    fid = context.festivals[name].id
    assert all(c.festival_id != fid for c in context.public)
