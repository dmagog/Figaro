# language: ru
"""Шаги для suggestions.feature (этап 4)."""
from behave import given, then, when
from sqlmodel import select

import _world as W
from figaro.domain.models import Concert, RouteSheetItem
from figaro.services import availability, sheets
from figaro.services.recommend import Prefs, weights_from


def _named(context):
    if not hasattr(context, "named"):
        context.named = {}
    return context.named


@given('в маршрутном листе концерты "{r1}" в зале "{h1}" и "{r2}" в зале "{h2}"')
def step_sheet_two(context, r1, h1, r2, h2):
    W.ensure_festival(context)
    context.sheet = sheets.create_empty(context.session, context.actor.id, context.festival.id)
    for r, h in ((r1, h1), (r2, h2)):
        s, e = r.split("-")
        dur = (W.at(e) - W.at(s)).seconds // 60
        W.add_item(context, W.concert(context, h, W.at(s), dur=dur))
    # кандидаты: помещающийся (11:30-12:15) и накладывающийся (10:30-11:15)
    context.fit_candidate = W.concert(context, "A", W.at("11:30"), dur=45)
    W.concert(context, "A", W.at("10:30"), dur=45)


@given('концерт-кандидат "{k}" распродан')
def step_candidate_soldout(context, k):
    c = W.concert(context, "A", W.at("12:00"), dur=30)
    _named(context)[k] = c
    availability.set_on_sale(context.session, c.id, False)


@given('среди кандидатов есть концерт с той же программой "{p}"')
def step_candidate_program(context, p):
    prog = W.program(context, p)
    context.repeat_candidate = W.concert(context, "A", W.at("11:30"), dur=30, program_id=prog.id)


@given('заполнена анкета с любимым автором "{author}"')
def step_anketa_fav(context, author):
    context.prof = weights_from(Prefs(favorite_authors=frozenset({author})))
    fav = W.concert(context, "A", W.at("11:35"), dur=30)
    W.attach_author(context, fav, author)
    context.fav_candidate = fav


@when('я запрашиваю "что добавить"')
def step_request_suggestions(context):
    context.suggestions = sheets.suggest_additions(
        context.session, context.sheet, getattr(context, "prof", None))


@then('предлагаются концерты, помещающиеся в окно между "{t1}" и "{t2}" с допустимым переходом')
def step_fitting_suggested(context, t1, t2):
    ids = [s.concert_id for s in context.suggestions]
    assert context.fit_candidate.id in ids


@then('не предлагаются концерты, создающие накладку')
def step_no_overlap_suggested(context):
    bad = context.session.exec(select(Concert).where(Concert.starts_at == W.at("10:30"))).first()
    ids = [s.concert_id for s in context.suggestions]
    assert bad.id not in ids


@then('"{k}" отсутствует в подсказках')
def step_k_absent(context, k):
    ids = [s.concert_id for s in context.suggestions]
    assert _named(context)[k].id not in ids


@then('концерты, уже добавленные в лист, отсутствуют в подсказках')
def step_chosen_absent(context):
    chosen = {it.concert_id for it in context.session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == context.sheet.id)).all()}
    ids = {s.concert_id for s in context.suggestions}
    assert not (chosen & ids)


@then('этот кандидат помечен как повтор программы')
def step_candidate_repeat(context):
    s = next(s for s in context.suggestions if s.concert_id == context.repeat_candidate.id)
    assert s.is_repeat


@then('кандидаты с произведениями "{author}" стоят выше')
def step_fav_higher(context, author):
    ids = [s.concert_id for s in context.suggestions]
    assert ids and ids[0] == context.fav_candidate.id


@then('у каждого кандидата указано, в какую щель он встаёт и сколько времени на переход')
def step_each_explained(context):
    assert context.suggestions
    for s in context.suggestions:
        assert s.after_id is not None or s.before_id is not None
        assert s.transition_minutes is not None
