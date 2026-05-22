"""Фаза предрасчёта дневных маршрутов (этап 2, docs/03#когда-и-для-каких-дней-считаем).

Покрывает ВСЕ дни фестиваля; идемпотентно по дню (повторный прогон перестраивает
только нужный день). Шаг конвейера создания фестиваля до активации.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from sqlmodel import Session, select

from figaro.domain.models import (Archetype, Author, Composition, Concert,
                                  ConcertComposition, ConcertGenre, DayRoute,
                                  DayRouteConcert, FestivalDay, Genre, Hall,
                                  HallTransition)
from figaro.domain.routing.conflicts import TransitionConfig, TransitionResolver
from figaro.domain.routing.dayroutes import (ConcertLite, build_day_routes,
                                            pareto_filter)


def build_resolver(session: Session, fid: int) -> TransitionResolver:
    matrix = {(t.from_hall_id, t.to_hall_id): t.minutes for t in session.exec(
        select(HallTransition).where(HallTransition.festival_id == fid)).all()}
    coords = {}
    for h in session.exec(select(Hall).where(Hall.festival_id == fid)).all():
        if h.lat is not None and h.lon is not None:
            coords[h.id] = (h.lat, h.lon)
    return TransitionResolver(matrix=matrix, coords=coords, config=TransitionConfig())


def _concert_lite(session: Session, c: Concert) -> ConcertLite:
    genre = session.exec(select(Genre.name).where(
        Genre.id == ConcertGenre.genre_id, ConcertGenre.concert_id == c.id)).first()
    authors = set(session.exec(select(Author.name).where(
        Author.id == Composition.author_id,
        Composition.id == ConcertComposition.composition_id,
        ConcertComposition.concert_id == c.id)).all())
    return ConcertLite(id=c.id, hall=c.hall_id, start=c.starts_at,
                       end=c.starts_at + timedelta(minutes=c.duration_min),
                       genre=genre, authors=frozenset(authors), price_kopecks=c.price_kopecks)


def _clear_day(session: Session, fid: int, day_id: int) -> None:
    routes = session.exec(select(DayRoute).where(
        DayRoute.festival_id == fid, DayRoute.festival_day_id == day_id)).all()
    for r in routes:
        for link in session.exec(select(DayRouteConcert).where(
                DayRouteConcert.day_route_id == r.id)).all():
            session.delete(link)
        session.delete(r)
    session.flush()


def precompute_day(session: Session, festival_id: int, day_id: int) -> int:
    fid = festival_id
    _clear_day(session, fid, day_id)
    concerts = session.exec(select(Concert).where(
        Concert.festival_id == fid, Concert.festival_day_id == day_id)).all()
    if not concerts:
        return 0
    resolver = build_resolver(session, fid)
    lites = [_concert_lite(session, c) for c in concerts]
    candidates = pareto_filter(build_day_routes(lites, resolver))
    # архетип (кластер) присваивается позже, на уровне фестиваля — assign_clusters
    for cand in candidates:
        dr = DayRoute(
            festival_id=fid, festival_day_id=day_id,
            concerts_count=cand.concerts_count, halls_count=cand.halls_count,
            show_minutes=cand.show_minutes, transition_minutes=cand.transition_minutes,
            wait_minutes=cand.wait_minutes, cost_kopecks=cand.cost_kopecks,
            hall_changes=cand.hall_changes, comfort_score=cand.comfort_score,
            diversity_score=cand.diversity_score)
        session.add(dr)
        session.flush()
        for pos, cid in enumerate(cand.concert_ids):
            session.add(DayRouteConcert(day_route_id=dr.id, concert_id=cid, position=pos))
    session.flush()
    return len(candidates)


def assign_clusters(session: Session, festival_id: int) -> List[Dict]:
    """Кластеризует ВСЕ дневные маршруты фестиваля → архетипы (data-driven, k по силуэту).

    Идемпотентно: сбрасывает ссылки маршрутов, удаляет старые архетипы и пересоздаёт.
    """
    from figaro.batch.clustering import FEATURES, cluster_routes

    routes = session.exec(select(DayRoute).where(DayRoute.festival_id == festival_id)).all()
    for r in routes:
        r.archetype_id = None
        session.add(r)
    session.flush()
    for old in session.exec(select(Archetype).where(Archetype.festival_id == festival_id)).all():
        session.delete(old)
    session.flush()
    if not routes:
        return []

    rows = [{f: getattr(r, f) for f in FEATURES} for r in routes]
    labels, clusters = cluster_routes(rows)
    arch_ids = []
    for c in clusters:
        a = Archetype(festival_id=festival_id, key=c["key"], title=c["title"],
                      description=c["description"])
        session.add(a)
        session.flush()
        arch_ids.append(a.id)
    for r, lab in zip(routes, labels):
        r.archetype_id = arch_ids[lab]
        session.add(r)
    session.flush()
    return clusters


def precompute_festival(session: Session, festival_id: int) -> Dict[int, int]:
    """Предрасчёт по ВСЕМ дням фестиваля + кластеризация маршрутов. Возвращает {day_id: число}."""
    stats = {}
    for day in session.exec(select(FestivalDay).where(
            FestivalDay.festival_id == festival_id)).all():
        stats[day.id] = precompute_day(session, festival_id, day.id)
    assign_clusters(session, festival_id)
    return stats
