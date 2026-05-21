"""Ленивая сборка фестивальных маршрутов из дневных (docs/03).

Фестивальный маршрут = по одному дневному маршруту с каждого дня.
top-k над произведением — куча (k-best), без полного перебора.
Аддитивные признаки суммируются; разнообразие — по объединению.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class DayRouteView:
    score: float
    concerts_count: int = 0
    show_minutes: int = 0
    transition_minutes: int = 0
    wait_minutes: int = 0
    cost_kopecks: int = 0
    genres: frozenset = field(default_factory=frozenset)
    authors: frozenset = field(default_factory=frozenset)
    ref: object = None  # ссылка на исходный дневной маршрут (id и т.п.)


@dataclass
class FestivalRouteView:
    days: Tuple[DayRouteView, ...]
    score: float
    concerts_count: int
    show_minutes: int
    transition_minutes: int
    wait_minutes: int
    cost_kopecks: int
    genres: frozenset    # объединение
    authors: frozenset   # объединение


def _aggregate(combo: Tuple[DayRouteView, ...]) -> FestivalRouteView:
    genres = frozenset().union(*[d.genres for d in combo]) if combo else frozenset()
    authors = frozenset().union(*[d.authors for d in combo]) if combo else frozenset()
    return FestivalRouteView(
        days=combo,
        score=sum(d.score for d in combo),
        concerts_count=sum(d.concerts_count for d in combo),
        show_minutes=sum(d.show_minutes for d in combo),
        transition_minutes=sum(d.transition_minutes for d in combo),
        wait_minutes=sum(d.wait_minutes for d in combo),
        cost_kopecks=sum(d.cost_kopecks for d in combo),
        genres=genres,      # по объединению, не сумма
        authors=authors,
    )


def top_k_festival(day_lists: List[List[DayRouteView]], k: int) -> List[FestivalRouteView]:
    """top-k комбинаций (по 1 дневному с каждого дня) по аддитивному скору, без полного перебора.

    Каждый day_list должен быть отсортирован по убыванию score.
    Алгоритм: k-best над декартовым произведением через кучу соседних индексов.
    """
    lists = [lst for lst in day_lists if lst]
    if not lists:
        return []
    dims = len(lists)

    def combo_score(idx: Tuple[int, ...]) -> float:
        return sum(lists[d][idx[d]].score for d in range(dims))

    start = tuple([0] * dims)
    seen = {start}
    heap: List[Tuple[float, Tuple[int, ...]]] = [(-combo_score(start), start)]
    out: List[FestivalRouteView] = []
    while heap and len(out) < k:
        neg, idx = heapq.heappop(heap)
        out.append(_aggregate(tuple(lists[d][idx[d]] for d in range(dims))))
        for d in range(dims):
            nb = list(idx)
            nb[d] += 1
            if nb[d] < len(lists[d]):
                t = tuple(nb)
                if t not in seen:
                    seen.add(t)
                    heapq.heappush(heap, (-combo_score(t), t))
    return out
