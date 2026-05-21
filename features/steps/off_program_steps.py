# language: ru
"""Шаги для off_program.feature (этап 8)."""
from behave import given, then, when
from sqlmodel import select

import _world as W
from figaro.domain.models import OffProgram
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services import sheets


def _events(context):
    if not hasattr(context, "events"):
        context.events = {}
    return context.events


def _range(r):
    s, e = r.split("-")
    return W.at(s), (W.at(e) - W.at(s)).seconds // 60


def _make_event(context, title, r, hall_name, recommend):
    fid = context.festival.id
    h = W.hall(context, hall_name)
    starts, dur = _range(r)
    op = OffProgram(festival_id=fid, title=title, starts_at=starts, duration_min=dur,
                    hall_id=h.id, is_recommended=recommend)
    context.session.add(op)
    context.session.flush()
    _events(context)[title] = op
    return op


# --- импорт офф-программы ---
@given('выгрузка с внепрограммными событиями')
def step_src_offprogram(context):
    W.ensure_festival(context)
    context.src = S.CatalogSource(
        halls=[S.HallRow("A", seats=100)],
        off_program=[
            S.OffProgramRow(external_num=1, title="Лекция о Бахе", hall_name="A",
                            starts_at="2026-07-01 11:30:00", duration_min=45, recommend=True),
            S.OffProgramRow(external_num=2, title="Выставка афиш", hall_name="A",
                            starts_at="2026-07-01 16:00:00", duration_min=60, recommend=False),
        ])


@when('импорт каталога загружает офф-программу')
def step_import_offprogram(context):
    import_catalog(context.session, context.festival.id, context.src)


@when('импорт офф-программы выполняется дважды')
def step_import_offprogram_twice(context):
    import_catalog(context.session, context.festival.id, context.src)
    import_catalog(context.session, context.festival.id, context.src)


@then('события офф-программы привязаны к активному фестивалю')
def step_offprogram_scoped(context):
    ops = context.session.exec(select(OffProgram).where(
        OffProgram.festival_id == context.festival.id)).all()
    assert len(ops) == 2 and all(op.festival_id == context.festival.id for op in ops)


@then('рекомендованные события помечены флагом')
def step_offprogram_recommended_flag(context):
    ops = context.session.exec(select(OffProgram).where(
        OffProgram.festival_id == context.festival.id)).all()
    assert any(op.is_recommended for op in ops) and any(not op.is_recommended for op in ops)


@then('каждое внепрограммное событие присутствует ровно один раз')
def step_offprogram_no_duplicates(context):
    ops = context.session.exec(select(OffProgram).where(
        OffProgram.festival_id == context.festival.id)).all()
    nums = [op.external_num for op in ops]
    assert len(ops) == 2 and len(nums) == len(set(nums)), nums


# --- подсказки офф-программы для маршрута ---
@given('внепрограммное событие "{title}" "{r}" в зале "{hall}"')
def step_event(context, title, r, hall):
    _make_event(context, title, r, hall, recommend=False)


@given('рекомендованное внепрограммное событие "{title}" "{r}" в зале "{hall}"')
def step_event_recommended(context, title, r, hall):
    _make_event(context, title, r, hall, recommend=True)


@when('я запрашиваю офф-программу для маршрута')
def step_request_offprogram(context):
    context.offsug = sheets.suggest_off_program(context.session, context.sheet)


@then('событие "{title}" есть среди предложенных')
def step_event_suggested(context, title):
    titles = [s.title for s in context.offsug]
    assert title in titles, titles


@then('событие "{title}" отсутствует среди предложенных')
def step_event_not_suggested(context, title):
    titles = [s.title for s in context.offsug]
    assert title not in titles, titles


@then('рекомендованное событие "{top}" стоит выше "{other}"')
def step_event_ranked_higher(context, top, other):
    titles = [s.title for s in context.offsug]
    assert top in titles and other in titles, titles
    assert titles.index(top) < titles.index(other), titles
