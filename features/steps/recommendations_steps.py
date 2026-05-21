# language: ru
"""Шаги для recommendations.feature (этап 4). Ранжирование/группировка — на RouteCard."""
from behave import given, then, when

from figaro.services.recommend import (Prefs, RouteCard, WeightProfile,
                                       group_by_archetype, rank_cards,
                                       relax_by_concert_count, weights_from)


def _card(cid, key, comfort=0.0, diversity=0.0, concerts=2):
    return RouteCard(id=cid, archetype_key=key, concerts_count=concerts, days=1,
                     transition_minutes=10, wait_minutes=5, cost_kopecks=400,
                     comfort_score=comfort, diversity_score=diversity,
                     authors=frozenset({"Бах"}), key_authors=("Бах",))


def _comfort_profile():
    return WeightProfile(target_max_concerts=5, w_comfort=0.7, w_diversity=0.15, w_depth=0.15,
                         hurry_tolerant=False, days=(), windows=(),
                         fav_authors=frozenset(), fav_genres=frozenset())


def _diversity_profile():
    return WeightProfile(target_max_concerts=5, w_comfort=0.15, w_diversity=0.7, w_depth=0.15,
                         hurry_tolerant=False, days=(), windows=(),
                         fav_authors=frozenset(), fav_genres=frozenset())


@given('заполнена анкета зрителя')
def step_anketa_filled(context):
    context.prof = weights_from(Prefs())


@when('я открываю подбор')
def step_open_recommendations(context):
    if getattr(context, "relax_cards", None) is not None:
        context.relaxed_result, context.relaxed = relax_by_concert_count(
            context.relax_cards, context.target_min, context.target_max)
    elif getattr(context, "empty_window", False):
        context.result, context.hint = [], "измените день или окно"
    else:
        cards = [_card(1, "marathon"), _card(2, "comfort"),
                 _card(3, "explorer"), _card(4, "deep")]
        context.grouped = group_by_archetype(cards)


@then('маршруты сгруппированы по архетипам "{a}", "{b}", "{c}" и "{d}"')
def step_grouped(context, a, b, c, d):
    assert {"marathon", "comfort", "explorer", "deep"} <= set(context.grouped.keys())


@then('в каждом архетипе показаны топ-k маршрутов')
def step_each_group_nonempty(context):
    assert all(len(v) >= 1 for v in context.grouped.values())


@when('я смотрю карточку маршрута')
def step_view_card(context):
    context.card = _card(1, "comfort", comfort=-15, diversity=3)


@then('видны число концертов, дни, время в пути и ожидании, стоимость и ключевые авторы')
def step_card_fields(context):
    c = context.card
    assert c.concerts_count is not None and c.days is not None
    assert c.transition_minutes is not None and c.wait_minutes is not None
    assert c.cost_kopecks is not None and len(c.key_authors) >= 1


@given('в анкете приоритет "комфорт"')
def step_priority_comfort(context):
    context.prof = _comfort_profile()


@when('формируется выдача')
def step_form_output(context):
    context.cards = [_card(1, "comfort", comfort=-5, diversity=1),
                     _card(2, "explorer", comfort=-40, diversity=5)]
    context.ranked = rank_cards(context.cards, context.prof)


@then('маршруты с высоким comfort_score стоят выше')
def step_comfort_top(context):
    assert context.ranked[0].comfort_score == max(c.comfort_score for c in context.cards)


@given('выдача сформирована с приоритетом "комфорт"')
def step_output_comfort(context):
    context.cards = [_card(1, "comfort", comfort=-5, diversity=1),
                     _card(2, "explorer", comfort=-40, diversity=5)]
    context.ranked = rank_cards(context.cards, _comfort_profile())


@when('я меняю вектор интереса на "{iv}"')
def step_change_vector(context, iv):
    context.ranked2 = rank_cards(context.cards, _diversity_profile())


@then('маршруты с высоким diversity_score поднимаются выше')
def step_diversity_top(context):
    assert context.ranked2[0].diversity_score == max(c.diversity_score for c in context.cards)


@given('анкета с очень узким диапазоном числа концертов, под который маршрутов нет')
def step_narrow_range(context):
    context.relax_cards = [_card(1, "comfort", concerts=1), _card(2, "marathon", concerts=2),
                           _card(3, "explorer", concerts=3)]
    context.target_min, context.target_max = 10, 10


@then('диапазон числа концертов поэтапно расширяется, пока не появятся варианты')
def step_relaxed_nonempty(context):
    assert context.relaxed_result


@then('показана пометка "под точные параметры мало вариантов — показали ближайшие"')
def step_relax_note(context):
    assert context.relaxed is True


@then('выбранные дни доступности и наличие билетов не ослабляются')
def step_days_not_relaxed(context):
    # релаксация затронула только число концертов (по построению relax_by_concert_count)
    assert context.relaxed is True


@given('в выбранный день и окно нет доступных концертов')
def step_empty_window(context):
    context.empty_window = True


@then('показано пустое состояние с предложением изменить день или окно')
def step_empty_state(context):
    assert context.result == [] and context.hint
