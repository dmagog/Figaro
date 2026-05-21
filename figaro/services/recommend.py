"""Анкета → веса ранжирования и фильтры (этап 3, docs/03#анкета-и-веса).

4 шага анкеты влияют на выдачу: темп, дни/окна (жёсткий фильтр),
вектор интереса (вес разнообразия vs глубины), любимые авторы/жанры (бонус, не фильтр).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Tuple

_PACE = {"расслабленно": "relaxed", "relaxed": "relaxed",
         "марафон": "marathon", "marathon": "marathon",
         "баланс": "balanced", "balanced": "balanced"}
_INTEREST = {"открывать новое": "new", "new": "new",
             "глубже в любимое": "deep", "deep": "deep"}

MARATHON_TARGET = 99


@dataclass
class Prefs:
    pace: Optional[str] = None
    interest_vector: Optional[str] = None
    available_days: Tuple[int, ...] = ()
    time_windows: Tuple[str, ...] = ()
    favorite_authors: FrozenSet[str] = frozenset()
    favorite_genres: FrozenSet[str] = frozenset()


@dataclass
class WeightProfile:
    target_max_concerts: int
    w_comfort: float
    w_diversity: float
    w_depth: float
    hurry_tolerant: bool
    days: Tuple[int, ...]
    windows: Tuple[str, ...]
    fav_authors: FrozenSet[str]
    fav_genres: FrozenSet[str]


def weights_from(prefs: Prefs) -> WeightProfile:
    target, wc, wd, wp, tol = 5, 0.34, 0.33, 0.33, False

    pace = _PACE.get((prefs.pace or "").strip().lower())
    if pace == "relaxed":
        target, wc, wd, wp, tol = 3, 0.6, 0.2, 0.2, False
    elif pace == "marathon":
        target, wc, wd, wp, tol = MARATHON_TARGET, 0.1, 0.45, 0.45, True

    interest = _INTEREST.get((prefs.interest_vector or "").strip().lower())
    if interest == "new":
        wd, wp = max(wd, 0.5), min(wp, 0.2)
    elif interest == "deep":
        wp, wd = max(wp, 0.5), min(wd, 0.2)

    return WeightProfile(target_max_concerts=target, w_comfort=wc, w_diversity=wd, w_depth=wp,
                         hurry_tolerant=tol, days=tuple(prefs.available_days),
                         windows=tuple(prefs.time_windows),
                         fav_authors=frozenset(prefs.favorite_authors),
                         fav_genres=frozenset(prefs.favorite_genres))


@dataclass
class CandidateView:
    id: int
    day: int = 0
    window: str = ""
    genres: FrozenSet[str] = field(default_factory=frozenset)
    authors: FrozenSet[str] = field(default_factory=frozenset)
    comfort: float = 0.0
    diversity: float = 0.0
    depth: float = 0.0


def filter_candidates(cands, prof: WeightProfile):
    """Жёсткий фильтр по дням и окнам доступности (если заданы). Наличие/дни не ослабляются."""
    out = []
    for c in cands:
        if prof.days and c.day not in prof.days:
            continue
        if prof.windows and c.window not in prof.windows:
            continue
        out.append(c)
    return out


def favorites_bonus(cand: CandidateView, prof: WeightProfile) -> float:
    overlap = len(cand.authors & prof.fav_authors) + len(cand.genres & prof.fav_genres)
    return 0.5 * overlap


def score(cand: CandidateView, prof: WeightProfile) -> float:
    base = prof.w_comfort * cand.comfort + prof.w_diversity * cand.diversity + prof.w_depth * cand.depth
    return base + favorites_bonus(cand, prof)


def rank(cands, prof: WeightProfile):
    """Фильтр (жёсткий) → сортировка по скору (с бонусом за любимое)."""
    filtered = filter_candidates(cands, prof)
    return sorted(filtered, key=lambda c: score(c, prof), reverse=True)
