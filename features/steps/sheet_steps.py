# language: ru
"""Шаги для route_sheet.feature (этап 4)."""
from behave import given, then, when
from sqlmodel import select

import _world as W
from figaro.domain.models import (Concert, DayRoute, DayRouteConcert,
                                  RouteSheetItem)
from figaro.domain.routing.conflicts import Status
from figaro.services import availability, sheets


def _named(context):
    if not hasattr(context, "named"):
        context.named = {}
    return context.named


def _items(context):
    return context.session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == context.sheet.id)).all()


# 1. из готового маршрута
@given('подбор предложил маршрут "{name}"')
def step_route_offered(context, name):
    W.ensure_festival(context)
    W.transition(context, "A", "B", 10)
    c1 = W.concert(context, "A", W.at("13:00"))
    c2 = W.concert(context, "B", W.at("15:00"))
    dr = DayRoute(festival_id=context.festival.id, festival_day_id=c1.festival_day_id,
                  concerts_count=2)
    context.session.add(dr)
    context.session.flush()
    context.session.add(DayRouteConcert(day_route_id=dr.id, concert_id=c1.id, position=0))
    context.session.add(DayRouteConcert(day_route_id=dr.id, concert_id=c2.id, position=1))
    context.session.flush()
    context.route_id = dr.id


@when('я добавляю маршрут "{name}" в свой маршрутный лист')
def step_add_route(context, name):
    context.sheet = sheets.create_from_route(context.session, context.actor.id,
                                             context.festival.id, context.route_id, title=name)


@then('создаётся персистентный маршрутный лист с концертами маршрута "{name}"')
def step_sheet_created(context, name):
    assert context.sheet.id is not None and len(_items(context)) == 2


@then('лист принадлежит мне')
def step_sheet_mine(context):
    assert context.sheet.user_id == context.actor.id


# 2. с нуля
@given('у меня пустой маршрутный лист')
def step_empty_sheet(context):
    W.ensure_festival(context)
    context.sheet = sheets.create_empty(context.session, context.actor.id, context.festival.id)


@when('я добавляю концерт "{a}" и концерт "{b}"')
def step_add_two(context, a, b):
    named = _named(context)
    named[a] = W.concert(context, "A", W.at("13:00"))
    named[b] = W.concert(context, "A", W.at("15:00"))
    sheets.add_concert(context.session, context.sheet, named[a].id)
    sheets.add_concert(context.session, context.sheet, named[b].id)


@then('оба концерта в листе')
def step_both_in(context):
    assert len(_items(context)) == 2


@then('лист сохранён между заходами')
def step_persisted(context):
    assert len(_items(context)) == 2  # персистентно в БД


# 3. сложность перехода
@given('в листе есть концерт в зале "{hall}", заканчивающийся в "{t}"')
def step_sheet_concert_ending(context, hall, t):
    W.ensure_festival(context)
    end = W.at(t)
    start = end.replace(hour=end.hour - 1, minute=15)  # длительность 45 → конец = t
    c = W.concert(context, hall, start, dur=45)
    context.prev_hall = hall
    W.add_item(context, c)


@when('я добавляю концерт в зале "{hall}", начинающийся в "{t}"')
def step_add_concert_in_hall(context, hall, t):
    W.transition(context, context.prev_hall, hall, 15)
    c = W.concert(context, hall, W.at(t), dur=45)
    context.add_result = sheets.add_concert(context.session, context.sheet, c.id)


@then('концерт добавлен')
def step_added(context):
    assert context.add_result.added


@then('между ними показан статус перехода "{status}"')
def step_status_shown(context, status):
    assert context.add_result.status == Status(status), context.add_result.status


# 4. дополнение в щель
@given('в листе есть концерты в "{r1}" и "{r2}"')
def step_sheet_two_ranges(context, r1, r2):
    W.ensure_festival(context)
    for r in (r1, r2):
        s, e = r.split("-")
        dur = (W.at(e) - W.at(s)).seconds // 60
        W.add_item(context, W.concert(context, "A", W.at(s), dur=dur))


@given('система предложила релевантный концерт, помещающийся между ними')
def step_relevant_candidate(context):
    context.candidate = W.concert(context, "A", W.at("11:30"), dur=45)  # 11:30-12:15


@when('я добавляю этот концерт из подсказок')
def step_add_from_suggestions(context):
    context.add_result = sheets.add_concert(context.session, context.sheet, context.candidate.id)


@then('он встаёт в листе по своему времени между соседями')
def step_inserted_between(context):
    assert context.add_result.added


@then('статус переходов с соседями — "ok" или "tight"')
def step_status_ok_tight(context):
    assert context.add_result.status in (Status.OK, Status.TIGHT, Status.SAME_HALL)


# 5. накладка
@given('в листе есть концерт, идущий с "{t1}" до "{t2}"')
def step_sheet_concert_span(context, t1, t2):
    W.ensure_festival(context)
    dur = (W.at(t2) - W.at(t1)).seconds // 60
    W.add_item(context, W.concert(context, "A", W.at(t1), dur=dur))


@when('я пытаюсь добавить концерт, идущий с "{t1}" до "{t2}"')
def step_try_add_span(context, t1, t2):
    dur = (W.at(t2) - W.at(t1)).seconds // 60
    c = W.concert(context, "A", W.at(t1), dur=dur)
    context.add_result = sheets.add_concert(context.session, context.sheet, c.id)


@then('система сообщает о накладке "{status}"')
def step_overlap_reported(context, status):
    assert context.add_result.status == Status(status)


@then('концерт не добавляется')
def step_not_added(context):
    assert not context.add_result.added


# 6. повтор программы
@given('в листе есть концерт с программой "{p}"')
def step_sheet_program(context, p):
    W.ensure_festival(context)
    prog = W.program(context, p)
    W.add_item(context, W.concert(context, "A", W.at("13:00"), program_id=prog.id))


@when('я добавляю другой концерт с той же программой "{p}"')
def step_add_same_program(context, p):
    prog = W.program(context, p)
    c = W.concert(context, "A", W.at("15:00"), program_id=prog.id)
    context.add_result = sheets.add_concert(context.session, context.sheet, c.id)


@then('он помечен как "вы уже видели эту программу"')
def step_repeat_flag(context):
    assert context.add_result.is_repeat


# 7. удаление
@given('в листе есть концерты "{a}" и "{b}"')
def step_sheet_named_two(context, a, b):
    W.ensure_festival(context)
    named = _named(context)
    named[a] = W.concert(context, "A", W.at("13:00"))
    named[b] = W.concert(context, "A", W.at("15:00"))
    W.add_item(context, named[a])
    W.add_item(context, named[b])


@when('я убираю концерт "{a}"')
def step_remove(context, a):
    sheets.remove_concert(context.session, context.sheet, _named(context)[a].id)


@then('в листе остаётся только "{b}"')
def step_only_remains(context, b):
    items = _items(context)
    assert len(items) == 1 and items[0].concert_id == _named(context)[b].id


# 8. закреплённый
@given('в листе закреплён концерт "{k}"')
def step_pinned(context, k):
    W.ensure_festival(context)
    c = W.concert(context, "A", W.at("13:00"))
    _named(context)[k] = c
    W.add_item(context, c)
    sheets.set_pin(context.session, context.sheet, c.id, True)


@when('наличие меняется и выполняется пересчёт предложений')
def step_recompute(context):
    for k, c in _named(context).items():
        availability.set_on_sale(context.session, c.id, False)
    context.replacements = sheets.proposed_replacements(context.session, context.sheet)


@then('"{k}" остаётся в листе без предложения замены')
def step_pinned_stays(context, k):
    cid = _named(context)[k].id
    assert cid in [it.concert_id for it in _items(context)]
    assert cid not in context.replacements


# 9. распродан между показом и добавлением
@given('в подсказках есть концерт "{k}"')
def step_suggested_concert(context, k):
    W.ensure_festival(context)
    context.sheet = sheets.create_empty(context.session, context.actor.id, context.festival.id)
    _named(context)[k] = W.concert(context, "A", W.at("13:00"))
    W.concert(context, "A", W.at("15:00"))  # доступная альтернатива того же дня


@given('к моменту добавления концерт "{k}" стал "не в продаже"')
def step_soldout(context, k):
    availability.set_on_sale(context.session, _named(context)[k].id, False)


@when('я пытаюсь добавить "{k}" в лист')
def step_try_add_soldout(context, k):
    context.add_result = sheets.add_concert(context.session, context.sheet, _named(context)[k].id)


@then('добавление отклонено с пометкой "концерт распродан"')
def step_rejected_soldout(context):
    assert not context.add_result.added and "распродан" in (context.add_result.reason or "")


@then('мне предложена доступная альтернатива')
def step_alternative(context):
    assert context.add_result.alternative_id is not None
