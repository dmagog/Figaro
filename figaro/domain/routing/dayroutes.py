"""Дневные маршруты: DAG достижимости → перечисление путей → агрегаты/признаки → Pareto.

Чистый домен (без БД) — легко юнит-тестировать. Персистентность в DayRoute — в batch/precompute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Hashable, List

from figaro.domain.routing.conflicts import (PASSABLE, TransitionConfig,
                                             TransitionResolver, evaluate)


@dataclass
class ConcertLite:
    id: int
    hall: Hashable
    start: datetime
    end: datetime
    genre: object = None
    authors: frozenset = field(default_factory=frozenset)
    price_kopecks: int = 0


@dataclass
class RouteCandidate:
    concert_ids: List[int]
    concerts_count: int
    halls_count: int
    show_minutes: int
    transition_minutes: int
    wait_minutes: int
    cost_kopecks: int
    hall_changes: int
    genres: frozenset
    authors: frozenset

    @property
    def comfort_score(self) -> float:
        # меньше переходов/ожидания → комфортнее (выше)
        return -float(self.transition_minutes + self.wait_minutes)

    @property
    def diversity_score(self) -> float:
        return float(len(self.genres) + len(self.authors))


def _minutes(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)


def _make_candidate(seq: List[ConcertLite], resolver: TransitionResolver) -> RouteCandidate:
    show = sum(_minutes(c.start, c.end) for c in seq)
    trans = wait = changes = 0
    for prev, nxt in zip(seq, seq[1:]):
        walk = resolver.walk(prev.hall, nxt.hall) or 0
        gap = _minutes(prev.end, nxt.start)
        trans += walk
        wait += max(0, gap - walk)
        if prev.hall != nxt.hall:
            changes += 1
    genres = frozenset(c.genre for c in seq if c.genre)
    authors = frozenset().union(*[c.authors for c in seq]) if seq else frozenset()
    return RouteCandidate(
        concert_ids=[c.id for c in seq],
        concerts_count=len(seq),
        halls_count=len({c.hall for c in seq}),
        show_minutes=show,
        transition_minutes=trans,
        wait_minutes=wait,
        cost_kopecks=sum(c.price_kopecks for c in seq),
        hall_changes=changes,
        genres=genres,
        authors=authors,
    )


def build_day_routes(concerts: List[ConcertLite], resolver: TransitionResolver,
                     cfg: TransitionConfig | None = None, max_routes: int = 50000) -> List[RouteCandidate]:
    cfg = cfg or TransitionConfig()
    cs = sorted(concerts, key=lambda c: c.start)
    n = len(cs)
    adj = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(n):
            if i == j or cs[j].start < cs[i].end:
                continue
            walk = resolver.walk(cs[i].hall, cs[j].hall)
            if evaluate(cs[i].end, cs[j].start, cs[i].hall, cs[j].hall, walk, cfg) in PASSABLE:
                adj[i].append(j)

    paths: List[List[int]] = []

    def dfs(path: List[int]) -> None:
        if len(paths) >= max_routes:
            return
        paths.append(list(path))
        for j in adj[path[-1]]:
            path.append(j)
            dfs(path)
            path.pop()

    for i in range(n):
        dfs([i])

    return [_make_candidate([cs[k] for k in p], resolver) for p in paths]


def _objectives(c: RouteCandidate):
    # «больше — лучше» по каждой оси
    return (c.concerts_count, -c.transition_minutes, -c.wait_minutes, c.diversity_score)


def pareto_filter(cands: List[RouteCandidate]) -> List[RouteCandidate]:
    objs = [_objectives(c) for c in cands]
    keep = []
    for i in range(len(cands)):
        dominated = False
        for j in range(len(cands)):
            if i == j:
                continue
            a, b = objs[j], objs[i]
            if all(x >= y for x, y in zip(a, b)) and any(x > y for x, y in zip(a, b)):
                dominated = True
                break
        if not dominated:
            keep.append(cands[i])
    return keep
