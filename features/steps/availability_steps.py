# language: ru
"""Шаги для availability.feature (этап 5)."""
from datetime import datetime, timedelta

from behave import given, step, then, when
from sqlmodel import select

import _world as W
from figaro.domain.clock import FestivalClock
from figaro.domain.models import (Archetype, Artist, AvailabilitySnapshot,
                                  ConcertArtist, ConcertAvailability, DayRoute,
                                  DayRouteConcert, Purchase)
from figaro.importing.seed import _get_or_create
from figaro.services import availability, cache
from figaro.services.recommend import Prefs, recommend, weights_from


def _named(context):
    if not hasattr(context, "named"):
        context.named = {}
    return context.named


class _FakeRealNaive:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t = self.t + timedelta(**kw)


def _concert(context, name, start, popular=False, capacity=50):
    c = W.concert(context, "A", start, dur=45)
    c.capacity = capacity
    context.session.add(c)
    context.session.flush()
    if popular:
        a = _get_or_create(context.session, Artist, festival_id=context.festival.id,
                          name=f"Star-{name}")
        a.is_special = True
        context.session.add(a)
        context.session.flush()
        context.session.add(ConcertArtist(concert_id=c.id, artist_id=a.id))
        context.session.flush()
    _named(context)[name] = c
    return c


def _av(context, concert_id):
    return context.session.get(ConcertAvailability, concert_id)


# 1. кривая: популярные раньше
@given('режим наличия "{mode}" с фиксированным seed')
def step_mode_seed(context, mode):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, mode, seed=42)


@given('концерт "{a}" помечен популярным, а концерт "{b}" — нет')
def step_two_concerts_pop(context, a, b):
    _concert(context, a, datetime(2026, 6, 25, 19, 0), popular=True)
    _concert(context, b, datetime(2026, 6, 25, 19, 0), popular=False)


@when('виртуальное время приближается к дате концертов')
def step_time_near(context):
    availability.recompute(context.session, context.festival.id,
                          datetime(2026, 6, 24), mode="sim_curve", seed=42)


@then('"{a}" распродаётся раньше, чем "{b}"')
def step_sold_sooner(context, a, b):
    av_a, av_b = _av(context, _named(context)[a].id), _av(context, _named(context)[b].id)
    assert av_a.tickets_left < av_b.tickets_left, (av_a.tickets_left, av_b.tickets_left)


# 2. воспроизводимость
@given('режим наличия "{mode}" с seed "{seed:d}"')
def step_mode_seed2(context, mode, seed):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, mode, seed=seed)
    _concert(context, "C", datetime(2026, 6, 25, 19, 0))


@when('я дважды прогоняю продажи до одной и той же виртуальной даты')
def step_run_twice(context):
    fid = context.festival.id
    availability.recompute(context.session, fid, datetime(2026, 6, 20), mode="sim_curve", seed=42)
    context.left1 = _av(context, _named(context)["C"].id).tickets_left
    availability.recompute(context.session, fid, datetime(2026, 6, 20), mode="sim_curve", seed=42)
    context.left2 = _av(context, _named(context)["C"].id).tickets_left


@then('остатки билетов совпадают в обоих прогонах')
def step_same_left(context):
    assert context.left1 == context.left2


# 3. реплей
@given('выбран режим наличия "{mode}"')
def step_mode_only(context, mode):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, mode)


@given('вместимость концерта "{k}" равна {cap:d}')
def step_capacity(context, k, cap):
    _concert(context, k, datetime(2026, 6, 25, 19, 0), capacity=cap)


@given('есть {n:d} покупки концерта "{k}" с датой не позже "{d}"')
def step_purchases(context, n, k, d):
    c = _named(context)[k]
    for i in range(n):
        context.session.add(Purchase(festival_id=context.festival.id, external_op_id=9000 + i,
                                     customer_external_id=f"c{i}", concert_id=c.id,
                                     purchased_at=datetime.fromisoformat(d) - timedelta(days=1)))
    context.session.flush()


@then('остаток билетов концерта "{k}" равен {n:d}')
def step_left_equals(context, k, n):
    availability.recompute(context.session, context.festival.id, context.clock.now(),
                          mode="sim_replay")
    assert _av(context, _named(context)[k].id).tickets_left == n


# 4. ускоренный тик + кэш
@given('режим наличия "{mode}" и часы в режиме "accelerated"')
def step_mode_accelerated(context, mode):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, mode)
    _concert(context, "C", datetime(2026, 6, 25, 19, 0))
    context.areal = _FakeRealNaive(datetime(2026, 1, 1, 12, 0))
    context.aclock = FestivalClock(real_now=context.areal)
    context.aclock.set_accelerated(datetime(2026, 6, 10), speed=60)
    cache.set(context.festival.id, ["cached"])


@when('проходит одна реальная минута')
def step_one_real_minute(context):
    context.areal.advance(seconds=60)
    availability.tick(context.session, context.festival.id, context.aclock)


@then('наличие пересчитано на новую виртуальную дату')
def step_recomputed(context):
    snaps = context.session.exec(select(AvailabilitySnapshot)).all()
    assert snaps


@then('кэш доступных маршрутов инвалидирован')
def step_cache_invalidated(context):
    assert cache.get(context.festival.id) is None


# 5. не затирает историю
@given('есть снимок наличия из источника "{src}"')
def step_snapshot_exists(context, src):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, "sim_curve")
    c = _concert(context, "C", datetime(2026, 6, 25, 19, 0))
    context.session.add(AvailabilitySnapshot(concert_id=c.id, at=datetime(2026, 6, 1),
                                             tickets_left=50, is_on_sale=True, source=src))
    context.session.flush()


@when('работает режим "{mode}"')
def step_mode_runs(context, mode):
    availability.recompute(context.session, context.festival.id, datetime(2026, 6, 20), mode=mode)


@then('исходный снимок "{src}" сохранён в истории снимков')
def step_history_kept(context, src):
    snaps = context.session.exec(select(AvailabilitySnapshot).where(
        AvailabilitySnapshot.source == src)).all()
    assert snaps


# 6. помечен не в продаже
@given('у концерта "{k}" остаток билетов стал 0')
def step_left_zero(context, k):
    W.ensure_festival(context)
    c = _concert(context, k, datetime(2026, 6, 25, 19, 0))
    context.left_zero_id = c.id


@when('обновляется наличие')
def step_update_av(context):
    availability.set_on_sale(context.session, context.left_zero_id, on_sale=False, tickets_left=0)


@then('концерт "{k}" помечен "не в продаже"')
def step_marked_off(context, k):
    assert _av(context, _named(context)[k].id).is_on_sale is False


# 7. распроданный убирает маршрут
@given('дневной маршрут содержит концерт "{k}"')
def step_route_with_k(context, k):
    W.ensure_festival(context)
    W.transition(context, "A", "B", 10)
    K = _concert(context, k, datetime(2026, 7, 1, 13, 0))
    other = _concert(context, "X", datetime(2026, 7, 1, 15, 0))
    fid = context.festival.id
    dr_with = DayRoute(festival_id=fid, festival_day_id=K.festival_day_id, concerts_count=1)
    dr_without = DayRoute(festival_id=fid, festival_day_id=other.festival_day_id, concerts_count=1)
    context.session.add_all([dr_with, dr_without])
    context.session.flush()
    context.session.add(DayRouteConcert(day_route_id=dr_with.id, concert_id=K.id, position=0))
    context.session.add(DayRouteConcert(day_route_id=dr_without.id, concert_id=other.id, position=0))
    context.session.flush()
    context.dr_with, context.dr_without = dr_with, dr_without


@when('концерт "{k}" становится "не в продаже"')
def step_k_off(context, k):
    availability.set_on_sale(context.session, _named(context)[k].id, on_sale=False, tickets_left=0)


@then('этот маршрут исчезает из доступных')
def step_route_gone(context):
    avail = {dr.id for dr in availability.available_day_routes(context.session, context.festival.id)}
    assert context.dr_with.id not in avail


@then('маршруты без "{k}" остаются доступными')
def step_others_remain(context, k):
    avail = {dr.id for dr in availability.available_day_routes(context.session, context.festival.id)}
    assert context.dr_without.id in avail


# 8. фильтр на уровне дневных маршрутов
@given('десятки тысяч дневных маршрутов')
def step_many_routes(context):
    W.ensure_festival(context)
    fid = context.festival.id
    context.routes = []
    for i in range(5):
        c = _concert(context, f"m{i}", datetime(2026, 7, 1, 13 + i, 0))
        dr = DayRoute(festival_id=fid, festival_day_id=c.festival_day_id, concerts_count=1)
        context.session.add(dr)
        context.session.flush()
        context.session.add(DayRouteConcert(day_route_id=dr.id, concert_id=c.id, position=0))
        context.routes.append((dr, c))
    context.session.flush()


@step('часть концертов распродана')
def step_some_sold(context):
    # распродаём концерт первого маршрута
    if getattr(context, "routes", None):
        availability.set_on_sale(context.session, context.routes[0][1].id, False, 0)
        context.sold_route_id = context.routes[0][0].id
    else:
        _ensure_recommend_setup(context)


@then('отсев недоступных идёт по дневным маршрутам до сборки по дням')
def step_filter_dayroutes(context):
    avail = {dr.id for dr in availability.available_day_routes(context.session, context.festival.id)}
    assert context.sold_route_id not in avail and len(avail) == 4


# 9. подбор только доступные
def _ensure_recommend_setup(context):
    from figaro.batch.precompute import precompute_festival
    W.ensure_festival(context)
    W.transition(context, "A", "B", 10)
    _concert(context, "r1", datetime(2026, 7, 1, 13, 0))
    context.sold = _concert(context, "r2", datetime(2026, 7, 1, 15, 0))
    precompute_festival(context.session, context.festival.id)
    availability.set_on_sale(context.session, context.sold.id, False, 0)


@when('зритель открывает подбор')
def step_open_recommend(context):
    if getattr(context, "routes", None) is None and getattr(context, "sold", None) is None:
        _ensure_recommend_setup(context)
    context.recommended = recommend(context.session, context.festival.id, weights_from(Prefs()))


@then('в выдаче нет маршрутов с распроданными концертами')
def step_no_soldout_in_output(context):
    for cards in context.recommended.values():
        for card in cards:
            assert availability.route_available(context.session, card.id)


# 10. админ переключает режим
@given('активен режим наличия "{mode}"')
def step_active_mode(context, mode):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, mode)
    _concert(context, "C", datetime(2026, 6, 25, 19, 0), capacity=5)


@when('администратор переключает режим на "{mode}" на пульте эмуляции')
def step_switch_mode(context, mode):
    availability.set_mode(context.session, context.festival.id, mode)


@then('последующие пересчёты наличия используют "{mode}"')
def step_recompute_uses(context, mode):
    availability.recompute(context.session, context.festival.id, datetime(2026, 6, 20))
    assert _av(context, _named(context)["C"].id).source == mode


# 11. ручной тик и сброс
@given('фестиваль в фазе "on_sale"')
def step_phase_on_sale(context):
    W.ensure_festival(context)
    availability.set_mode(context.session, context.festival.id, "sim_curve")
    _concert(context, "C", datetime(2026, 7, 1, 19, 0), capacity=50)
    context.areal = _FakeRealNaive(datetime(2026, 1, 1, 12, 0))
    context.aclock = FestivalClock(real_now=context.areal)
    context.aclock.set_offset(datetime(2026, 6, 15))


@when('администратор нажимает «сделать тик»')
def step_manual_tick(context):
    availability.tick(context.session, context.festival.id, context.aclock)


@then('наличие пересчитано на текущую виртуальную дату')
def step_tick_recomputed(context):
    assert context.session.exec(select(AvailabilitySnapshot)).all()


@when('администратор нажимает «сбросить наличие к старту продаж»')
def step_reset(context):
    availability.reset_to_sales_start(context.session, context.festival.id)


@then('все концерты снова в продаже с полной вместимостью')
def step_all_on_sale_full(context):
    from figaro.domain.models import Concert
    for c in context.session.exec(select(Concert).where(
            Concert.festival_id == context.festival.id)).all():
        av = _av(context, c.id)
        assert av.is_on_sale and av.tickets_left == c.capacity
