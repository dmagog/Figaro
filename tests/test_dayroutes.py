from datetime import datetime

from figaro.domain.routing.combine import DayRouteView, top_k_festival
from figaro.domain.routing.conflicts import (PASSABLE, TransitionConfig,
                                             TransitionResolver, evaluate)
from figaro.domain.routing.dayroutes import (ConcertLite, RouteCandidate,
                                            build_day_routes, pareto_filter)

CFG = TransitionConfig()
RESOLVER = TransitionResolver(matrix={("A", "B"): 5}, config=CFG)


def _c(cid, hall, sh, eh, genre=None, authors=()):
    return ConcertLite(id=cid, hall=hall, start=datetime(2026, 7, 1, *sh),
                       end=datetime(2026, 7, 1, *eh), genre=genre, authors=frozenset(authors))


def test_day_routes_only_reachable():
    concerts = [
        _c(1, "A", (10, 0), (10, 45)),
        _c(2, "B", (11, 0), (11, 45)),
        _c(3, "B", (10, 50), (11, 35)),
        _c(4, "A", (10, 30), (11, 15)),  # пересекается с 1 → не в одной цепочке
    ]
    routes = build_day_routes(concerts, RESOLVER, CFG)
    assert routes
    by_id = {c.id: c for c in concerts}
    for r in routes:
        seq = [by_id[i] for i in r.concert_ids]
        for prev, nxt in zip(seq, seq[1:]):
            walk = RESOLVER.walk(prev.hall, nxt.hall)
            st = evaluate(prev.end, nxt.start, prev.hall, nxt.hall, walk, CFG)
            assert st in PASSABLE, st
    # пара 1+4 (накладка) не встречается вместе
    assert not any(set([1, 4]).issubset(set(r.concert_ids)) for r in routes)


def _cand(concerts, trans, wait, div):
    return RouteCandidate(concert_ids=[0], concerts_count=concerts, halls_count=1,
                          show_minutes=0, transition_minutes=trans, wait_minutes=wait,
                          cost_kopecks=0, hall_changes=0,
                          genres=frozenset(range(div)), authors=frozenset())


def test_pareto_removes_dominated():
    x = _cand(concerts=2, trans=5, wait=0, div=2)
    y = _cand(concerts=2, trans=10, wait=5, div=1)  # хуже по всем → доминируется x
    kept = pareto_filter([x, y])
    assert x in kept and y not in kept


def test_pareto_keeps_incomparable():
    a = _cand(concerts=3, trans=20, wait=0, div=1)  # больше концертов, но дольше переходы
    b = _cand(concerts=1, trans=0, wait=0, div=1)   # комфортнее, но меньше концертов
    kept = pareto_filter([a, b])
    assert a in kept and b in kept


def test_top_k_festival_sorted_and_limited():
    day = lambda base: [DayRouteView(score=base + 2), DayRouteView(score=base + 1)]
    lists = [day(10), day(20), day(30)]  # 3 дня × 2 = 8 комбинаций
    out = top_k_festival(lists, k=5)
    assert len(out) == 5
    scores = [r.score for r in out]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == (12 + 22 + 32)  # лучшие с каждого дня


def test_top_k_aggregation_union_diversity():
    d1 = DayRouteView(score=1, concerts_count=2, cost_kopecks=400,
                      genres=frozenset({"Камерные"}), authors=frozenset({"Бах"}))
    d2 = DayRouteView(score=1, concerts_count=3, cost_kopecks=600,
                      genres=frozenset({"Симфонические"}), authors=frozenset({"Бах", "Шуман"}))
    out = top_k_festival([[d1], [d2]], k=1)
    fr = out[0]
    assert fr.concerts_count == 5 and fr.cost_kopecks == 1000     # аддитивно
    assert fr.genres == {"Камерные", "Симфонические"}             # объединение
    assert fr.authors == {"Бах", "Шуман"}                         # объединение (не сумма)
