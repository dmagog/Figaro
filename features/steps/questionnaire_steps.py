# language: ru
"""Шаги для questionnaire.feature (этап 3): анкета → веса/фильтры/бонус."""
from behave import given, then, when

from figaro.services.recommend import (MARATHON_TARGET, CandidateView, Prefs,
                                       filter_candidates, rank, score,
                                       weights_from)


@given('я выбрал темп "{pace}"')
def step_pace(context, pace):
    context.prefs = Prefs(pace=pace)


@given('я выбрал вектор интереса "{iv}"')
def step_interest(context, iv):
    context.prefs = Prefs(interest_vector=iv)


@when('формируются параметры подбора')
def step_build_params(context):
    context.prof = weights_from(context.prefs)


@when('формируются веса')
def step_build_weights(context):
    context.prof = weights_from(context.prefs)


@then('целевое число концертов в день не больше {n:d}')
def step_target_le(context, n):
    assert context.prof.target_max_concerts <= n, context.prof.target_max_concerts


@then('вес комфорта повышен')
def step_comfort_up(context):
    assert context.prof.w_comfort > 0.34, context.prof.w_comfort


@then('целевое число концертов в день максимально')
def step_target_max(context):
    assert context.prof.target_max_concerts == MARATHON_TARGET


@then('терпимость к статусам "hurry" и "tight" повышена')
def step_tolerant(context):
    assert context.prof.hurry_tolerant


@then('вес разнообразия выше веса глубины')
def step_div_gt_depth(context):
    assert context.prof.w_diversity > context.prof.w_depth


# --- дни/окна (жёсткий фильтр) ---
@given('в подборе есть маршруты на дни "{a}", "{b}" и "{c}"')
def step_routes_days(context, a, b, c):
    cands = []
    cid = 1
    for d in (int(a), int(b), int(c)):
        for w in ("вечер", "день"):
            cands.append(CandidateView(id=cid, day=d, window=w))
            cid += 1
    context.cands = cands


@when('я отметил доступность только в день "{d}" в окне "{w}"')
def step_availability(context, d, w):
    context.sel_day = int(d)
    prof = weights_from(Prefs(available_days=(int(d),), time_windows=(w,)))
    context.result = filter_candidates(context.cands, prof)


@then('в подборе остаются только маршруты дня "{d}" с концертами вечером')
def step_only_day_evening(context, d):
    assert context.result
    assert all(c.day == int(d) and c.window == "вечер" for c in context.result)


@then('маршруты других дней исключены')
def step_others_excluded(context):
    assert all(c.day == context.sel_day for c in context.result)


# --- любимые авторы (бонус, не фильтр) ---
@given('я отметил любимого автора "{author}"')
def step_fav_author(context, author):
    context.fav_author = author


@given('есть маршруты как с произведениями "{author}", так и без них')
def step_routes_with_without(context, author):
    context.cands = [CandidateView(id=1, authors=frozenset({author})),
                     CandidateView(id=2, authors=frozenset())]


@when('выполняется ранжирование')
def step_rank(context):
    context.prof = weights_from(Prefs(favorite_authors=frozenset({context.fav_author})))
    context.ranked = rank(context.cands, context.prof)


@then('маршруты с "{author}" получают бонус к скору')
def step_bonus(context, author):
    fav = next(c for c in context.cands if author in c.authors)
    non = next(c for c in context.cands if author not in c.authors)
    assert score(fav, context.prof) > score(non, context.prof)


@then('маршруты без "{author}" остаются в выдаче')
def step_non_fav_present(context, author):
    assert any(author not in c.authors for c in context.ranked)


# --- частичное заполнение ---
@given('я заполнил только шаг "{step}"')
def step_partial(context, step):
    context.prefs = Prefs(pace="баланс")


@when('я запрашиваю подбор')
def step_request(context):
    context.prof = weights_from(context.prefs)
    context.cands = [CandidateView(id=1, day=1, window="день"),
                     CandidateView(id=2, day=2, window="вечер")]
    context.ranked = rank(context.cands, context.prof)


@then('подбор формируется с дефолтными весами для остальных шагов')
def step_defaults(context):
    assert context.prof.days == () and context.prof.windows == ()
    assert context.prof.fav_authors == frozenset()


@then('выдача не пустая')
def step_non_empty(context):
    assert context.ranked
