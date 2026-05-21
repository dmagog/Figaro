# language: ru
"""Шаги для availability_import.feature (этап 7). Шаг 'помечен не в продаже' — из availability_steps."""
from datetime import datetime

from behave import given, then, when
from sqlmodel import select

import _world as W
from figaro.domain.models import (AvailabilitySnapshot, Concert,
                                  ConcertAvailability, Hall, Program)
from figaro.importing import source as S
from figaro.importing.availability import import_availability
from figaro.importing.seed import import_catalog
from figaro.services import availability, cache


def _named(context):
    if not hasattr(context, "named"):
        context.named = {}
    return context.named


def _av(context, cid):
    return context.session.get(ConcertAvailability, cid)


@given('концерт "{k}" в продаже с остатком {n:d}')
def step_concert_on_sale(context, k, n):
    W.ensure_festival(context)
    c = W.concert(context, "A", datetime(2026, 7, 1, 13, 0), dur=45)
    _named(context)[k] = c
    availability.set_on_sale(context.session, c.id, True, tickets_left=n, source="crm_import")
    cache.set(context.festival.id, ["cached"])


@when('администратор загружает файл, где у "{k}" остаток {n:d}')
def step_load_file(context, k, n):
    c = _named(context)[k]
    import_availability(context.session, context.festival.id, [(c.crm_show_id, n)],
                       now=datetime(2026, 6, 30))


@then('источник наличия концерта "{k}" — "{src}"')
def step_source(context, k, src):
    assert _av(context, _named(context)[k].id).source == src


@then('кэш доступных маршрутов пересчитан')
def step_cache_recomputed(context):
    assert cache.get(context.festival.id) is None


@given('загружен каталог концертов и программ')
def step_catalog_with_programs(context):
    W.ensure_festival(context)
    src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        concerts=[S.ConcertRow(1, 501, "K1", "A", datetime(2026, 7, 1, 13, 0), 45),
                  S.ConcertRow(2, 502, "K2", "A", datetime(2026, 7, 1, 15, 0), 45)],
        compositions=[S.CompositionRow(1, "Бах", "Ария"), S.CompositionRow(2, "Шуман", "Этюд")])
    import_catalog(context.session, context.festival.id, src)
    context.before_counts = (
        len(context.session.exec(select(Concert)).all()),
        len(context.session.exec(select(Hall)).all()),
        len(context.session.exec(select(Program)).all()))


@when('импортируется только файл остатков')
def step_import_only_remainders(context):
    import_availability(context.session, context.festival.id, [(501, 3), (502, 0)],
                       now=datetime(2026, 6, 30))


@then('состав концертов, залов и программ не изменился')
def step_catalog_unchanged(context):
    after = (len(context.session.exec(select(Concert)).all()),
             len(context.session.exec(select(Hall)).all()),
             len(context.session.exec(select(Program)).all()))
    assert after == context.before_counts


@when('администратор загружает файл остатков')
def step_load_remainders(context):
    W.ensure_festival(context)
    c = W.concert(context, "A", datetime(2026, 7, 1, 13, 0), dur=45)
    _named(context)["S"] = c
    context.import_now = datetime(2026, 6, 30)
    import_availability(context.session, context.festival.id, [(c.crm_show_id, 5)],
                       now=context.import_now)


@then('в историю снимков добавлена запись с источником "{src}" и виртуальным временем')
def step_snapshot_written(context, src):
    snaps = context.session.exec(select(AvailabilitySnapshot).where(
        AvailabilitySnapshot.source == src)).all()
    assert snaps and any(s.at == context.import_now for s in snaps)
