from datetime import date

import pytest
from sqlmodel import Session, select

from figaro.batch.clustering import FEATURES, cluster_routes
from figaro.batch.precompute import assign_clusters
from figaro.db import make_test_engine
from figaro.domain.models import Archetype, DayRoute, FestivalDay
from figaro.services.festival import create_festival


def _row(concerts, trans, wait, cost=0, diversity=0, changes=0):
    return dict(zip(FEATURES, [concerts, trans, wait, cost, diversity, changes]))


def test_cluster_routes_separates_two_groups():
    # две явные группы: «короткие комфортные» и «длинные плотные»
    short = [_row(2, 0, 0, diversity=1) for _ in range(6)]
    long_ = [_row(8, 90, 60, diversity=6) for _ in range(6)]
    labels, clusters = cluster_routes(short + long_)
    assert len(clusters) >= 2
    # внутри каждой исходной группы метка одна и та же, между группами — разная
    assert len(set(labels[:6])) == 1 and len(set(labels[6:])) == 1
    assert labels[0] != labels[6]
    assert all(c["title"] and c["description"] for c in clusters)


def test_cluster_routes_small_n_single_cluster():
    labels, clusters = cluster_routes([_row(2, 0, 0), _row(3, 10, 5)])
    assert set(labels) == {0} and len(clusters) == 1


def test_cluster_routes_deterministic():
    rows = [_row(i % 5 + 1, i * 3, i * 2, diversity=i % 4) for i in range(20)]
    a = cluster_routes(rows)
    b = cluster_routes(rows)
    assert a[0] == b[0] and [c["key"] for c in a[1]] == [c["key"] for c in b[1]]


def test_assign_clusters_labels_all_routes():
    s = Session(make_test_engine())
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    day = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    s.add(day)
    s.flush()
    # 12 маршрутов двух «характеров»
    for i in range(12):
        big = i % 2 == 0
        s.add(DayRoute(festival_id=f.id, festival_day_id=day.id,
                       concerts_count=8 if big else 2,
                       transition_minutes=90 if big else 0,
                       wait_minutes=60 if big else 0,
                       diversity_score=6.0 if big else 1.0))
    s.commit()
    clusters = assign_clusters(s, f.id)
    assert len(clusters) >= 2
    arch_ids = {a.id for a in s.exec(select(Archetype).where(Archetype.festival_id == f.id)).all()}
    routes = s.exec(select(DayRoute).where(DayRoute.festival_id == f.id)).all()
    assert routes and all(r.archetype_id in arch_ids for r in routes)
    # повторный прогон идемпотентен (не плодит архетипы сверх k)
    assign_clusters(s, f.id)
    assert len(s.exec(select(Archetype).where(Archetype.festival_id == f.id)).all()) == len(clusters)
