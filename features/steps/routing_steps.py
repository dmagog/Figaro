# language: ru
"""Шаги для transitions.feature и route_engine.feature (этап 2)."""
from datetime import date, datetime

from behave import given, then, when
from sqlmodel import select

from figaro.batch.precompute import precompute_day, precompute_festival
from figaro.domain.models import Concert, DayRoute, FestivalDay
from figaro.domain.routing.combine import DayRouteView, top_k_festival
from figaro.domain.routing.conflicts import (PASSABLE, Status, TransitionConfig,
                                             TransitionResolver, evaluate)
from figaro.domain.routing.dayroutes import (ConcertLite, RouteCandidate,
                                            build_day_routes, pareto_filter)
from figaro.importing import source as S
from figaro.importing.seed import import_catalog
from figaro.services.festival import create_festival

_PASSABLE_NAMES = {"ok", "tight", "same_hall", "same_building"}


def _at(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 7, 1, h, m)


def _resolver(context) -> TransitionResolver:
    return TransitionResolver(matrix=context.matrix, coords=context.coords, config=context.cfg)


# ============ transitions.feature ============
@given('пороги переходов: "впритык" = {tight:d} минут, допуск накладки = {slack:d} {unit}')
def step_thresholds(context, tight, slack, unit):
    context.cfg = TransitionConfig(buffer_tight_minutes=tight, buffer_overlap_slack=slack)
    context.matrix = {}
    context.coords = {}


@given('время перехода между залами "{a}" и "{b}" равно {m:d} {unit}')
def step_matrix_edge(context, a, b, m, unit):
    context.matrix[(a, b)] = m


@given('между залами "{a}" и "{b}" данных о переходе нет')
def step_no_data_edge(context, a, b):
    pass  # отсутствие в матрице/координатах — поведение по умолчанию


@given('концерт в зале "{hall}" заканчивается в "{t}"')
def step_prev_concert(context, hall, t):
    context.prev = (hall, _at(t))


@given('следующий концерт в зале "{hall}" начинается в "{t}"')
def step_next_concert(context, hall, t):
    context.next = (hall, _at(t))


@given('порог "впритык" изменён на {n:d} минут')
def step_change_tight(context, n):
    context.cfg.buffer_tight_minutes = n


@when('движок оценивает переход')
def step_evaluate(context):
    r = _resolver(context)
    (ph, pe), (nh, ns) = context.prev, context.next
    walk = r.walk(ph, nh)
    context.status = evaluate(pe, ns, ph, nh, walk, context.cfg)


@then('статус перехода — "{status}"')
def step_assert_status(context, status):
    assert context.status == Status(status), context.status


@given('пары залов "{a}"–"{b}" нет в матрице переходов')
def step_fg_no_matrix(context, a, b):
    context.fg = (a, b)
    context.matrix.pop((a, b), None)
    context.matrix.pop((b, a), None)


@given('у залов "{a}" и "{b}" заданы координаты')
def step_fg_coords(context, a, b):
    context.coords[a] = (56.838, 60.597)
    context.coords[b] = (56.842, 60.601)


@when('движок оценивает переход между ними')
def step_eval_between(context):
    a, b = context.fg
    r = _resolver(context)
    context.walk = r.walk(a, b)
    context.status = evaluate(_at("12:00"), _at("13:00"), a, b, context.walk, context.cfg)


@then('время перехода вычисляется по расстоянию и скорости пешком (`walk_speed`)')
def step_walk_estimated(context):
    assert context.walk is not None and context.walk >= 1, context.walk


@then('статус определяется по этому времени, а не "no_data"')
def step_status_not_nodata(context):
    assert context.status != Status.NO_DATA


def _build_demo_day(context):
    cfg = TransitionConfig()
    resolver = TransitionResolver(matrix={("A", "B"): 5}, config=cfg)
    concerts = [
        ConcertLite(1, "A", _at("10:00"), _at("10:45")),
        ConcertLite(2, "B", _at("11:00"), _at("11:45")),
        ConcertLite(3, "B", _at("10:50"), _at("11:35")),
    ]
    context.cands = pareto_filter(build_day_routes(concerts, resolver, cfg))
    context.demo = {c.id: c for c in concerts}
    context.demo_resolver, context.demo_cfg = resolver, cfg


@given('построены дневные маршруты')
def step_built_routes(context):
    _build_demo_day(context)


@when('я просматриваю любой предложенный маршрут')
def step_view_route(context):
    pass


def _assert_passable(context, allow_status_names):
    for r in context.cands:
        seq = [context.demo[i] for i in r.concert_ids]
        for prev, nxt in zip(seq, seq[1:]):
            walk = context.demo_resolver.walk(prev.hall, nxt.hall)
            st = evaluate(prev.end, nxt.start, prev.hall, nxt.hall, walk, context.demo_cfg)
            assert st.value in allow_status_names, st


@then('все его переходы имеют статус "ok", "tight", "same_hall" или "same_building"')
def step_all_passable(context):
    _assert_passable(context, _PASSABLE_NAMES)


@then('ни один переход не имеет статус "overlap"')
def step_no_overlap(context):
    for r in context.cands:
        seq = [context.demo[i] for i in r.concert_ids]
        for prev, nxt in zip(seq, seq[1:]):
            walk = context.demo_resolver.walk(prev.hall, nxt.hall)
            assert evaluate(prev.end, nxt.start, prev.hall, nxt.hall, walk, context.demo_cfg) != Status.OVERLAP


# ============ route_engine.feature ============
def _multiday_source():
    halls = [S.HallRow("A", seats=100), S.HallRow("B", seats=100)]
    transitions = [S.TransitionRow("A", "B", 10)]
    concerts, crm = [], 1
    for d in (1, 2, 3):
        concerts.append(S.ConcertRow(crm, crm, f"K{crm}", "A", datetime(2026, 7, d, 13, 0), 45, genre="Камерные"))
        crm += 1
        concerts.append(S.ConcertRow(crm, crm, f"K{crm}", "B", datetime(2026, 7, d, 15, 0), 45, genre="Симфонические"))
        crm += 1
    return S.CatalogSource(halls=halls, transitions=transitions, concerts=concerts)


@given('загружен каталог фестиваля')
def step_catalog_loaded(context):
    f = create_festival(context.session, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    context.festival = f
    import_catalog(context.session, f.id, _multiday_source())


@given('концерты дня с временами и залами, где переход возможен лишь в части пар')
def step_day_concerts(context):
    _build_demo_day(context)


@when('движок строит дневные маршруты')
def step_build_day_routes(context):
    pass  # уже построены в _build_demo_day


@then('каждый соседний переход имеет статус "ok", "tight", "same_hall" или "same_building"')
def step_each_passable(context):
    _assert_passable(context, _PASSABLE_NAMES)


@then('ни один маршрут не содержит статус "overlap" или "no_data"')
def step_no_overlap_nodata(context):
    _assert_passable(context, _PASSABLE_NAMES)  # passable исключает overlap/no_data


def _days_sorted(context):
    return sorted(context.session.exec(select(FestivalDay).where(
        FestivalDay.festival_id == context.festival.id)).all(), key=lambda d: d.day)


@given('фестиваль из 3 дней')
def step_three_days(context):
    assert len(_days_sorted(context)) == 3


@when('выполняется фаза предрасчёта дневных маршрутов')
def step_precompute(context):
    context.stats = precompute_festival(context.session, context.festival.id)


@then('дневные маршруты построены для каждого из 3 дней')
def step_routes_each_day(context):
    assert len(context.stats) == 3


@then('ни один день не остаётся без предрассчитанных маршрутов')
def step_each_day_nonempty(context):
    assert all(v > 0 for v in context.stats.values()), context.stats


def _day_route_ids(context, day_id):
    return sorted(r.id for r in context.session.exec(select(DayRoute).where(
        DayRoute.festival_id == context.festival.id, DayRoute.festival_day_id == day_id)).all())


@given('дневные маршруты построены для всех дней')
def step_all_days_built(context):
    precompute_festival(context.session, context.festival.id)
    context.before = {d.id: _day_route_ids(context, d.id) for d in _days_sorted(context)}


@when('из-за форс-мажора пересчитывается только день "{n:d}"')
def step_recompute_day(context, n):
    day = _days_sorted(context)[n - 1]
    context.recomputed_day = day.id
    precompute_day(context.session, context.festival.id, day.id)


@then('маршруты дня "{n:d}" перестроены')
def step_day_rebuilt(context, n):
    day = _days_sorted(context)[n - 1]
    assert _day_route_ids(context, day.id) != context.before[day.id]


@then('маршруты дней "{a:d}" и "{b:d}" не изменились')
def step_other_days_unchanged(context, a, b):
    days = _days_sorted(context)
    for n in (a, b):
        day = days[n - 1]
        assert _day_route_ids(context, day.id) == context.before[day.id]


def _cand(concerts, trans, wait, div):
    return RouteCandidate(concert_ids=[concerts], concerts_count=concerts, halls_count=1,
                          show_minutes=0, transition_minutes=trans, wait_minutes=wait,
                          cost_kopecks=0, hall_changes=0,
                          genres=frozenset(range(div)), authors=frozenset())


@given('маршрут "X" не хуже маршрута "Y" по всем признакам и лучше хотя бы по одному')
def step_dominance(context, ):
    context.x = _cand(2, 5, 0, 2)
    context.y = _cand(2, 10, 5, 1)
    context.cands = [context.x, context.y]


@when('выполняется Pareto-отсев')
def step_pareto(context):
    context.kept = pareto_filter(context.cands)


@then('маршрут "Y" исключён из набора')
def step_y_excluded(context):
    assert context.y not in context.kept


@then('маршрут "X" остаётся')
def step_x_kept(context):
    assert context.x in context.kept


@given('дневные маршруты по 3 дням')
def step_three_day_lists(context):
    mk = lambda base: [DayRouteView(score=base + 2), DayRouteView(score=base + 1)]
    context.day_lists = [mk(10), mk(20), mk(30)]


@when('я запрашиваю топ-5 фестивальных маршрутов')
def step_topk(context):
    context.fest = top_k_festival(context.day_lists, 5)


@then('возвращается 5 комбинаций, отсортированных по убыванию скора')
def step_topk_sorted(context):
    scores = [r.score for r in context.fest]
    assert len(context.fest) == 5 and scores == sorted(scores, reverse=True)


@then('фестивальные маршруты не материализуются как отдельные записи в БД')
def step_not_materialized(context):
    from sqlalchemy import inspect

    from figaro.domain.routing.combine import FestivalRouteView
    assert all(isinstance(r, FestivalRouteView) for r in context.fest)
    # нет таблицы фестивальных маршрутов — они существуют только в памяти
    tables = inspect(context.engine).get_table_names()
    assert not any("festivalroute" in t for t in tables), tables


@given('фестивальный маршрут из дневных маршрутов "D1" и "D2"')
def step_fest_from_two(context):
    d1 = DayRouteView(score=1, concerts_count=2, cost_kopecks=400, show_minutes=90,
                      genres=frozenset({"Камерные"}), authors=frozenset({"Бах"}))
    d2 = DayRouteView(score=1, concerts_count=3, cost_kopecks=600, show_minutes=135,
                      genres=frozenset({"Симфонические"}), authors=frozenset({"Бах", "Шуман"}))
    context.fr = top_k_festival([[d1], [d2]], 1)[0]


@when('считаются его признаки')
def step_compute_features(context):
    pass


@then('стоимость и время равны сумме по дням')
def step_additive(context):
    assert context.fr.cost_kopecks == 1000 and context.fr.show_minutes == 225


@then('разнообразие пересчитано по объединению концертов, а не суммой')
def step_union_diversity(context):
    assert context.fr.genres == {"Камерные", "Симфонические"}
    assert context.fr.authors == {"Бах", "Шуман"}  # объединение: 2, а не 3
