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


# ============ подбор по архетипам над предрассчитанными DayRoute (этап 4) ============
@dataclass
class RouteCard:
    id: int
    archetype_key: str
    concerts_count: int
    days: int
    transition_minutes: int
    wait_minutes: int
    cost_kopecks: int
    comfort_score: float
    diversity_score: float
    authors: FrozenSet[str] = field(default_factory=frozenset)
    key_authors: tuple = ()


def _minmax(vals):
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return [1.0 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]


def rank_cards(cards, prof: WeightProfile):
    """Нормируем comfort/diversity внутри набора, складываем с весами + бонус за любимое."""
    if not cards:
        return []
    cn = _minmax([c.comfort_score for c in cards])
    dn = _minmax([c.diversity_score for c in cards])
    scored = []
    for i, c in enumerate(cards):
        bonus = 0.5 * len(set(c.authors) & set(prof.fav_authors))
        s = prof.w_comfort * cn[i] + prof.w_diversity * dn[i] + bonus
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]


def group_by_archetype(cards):
    out = {}
    for c in cards:
        out.setdefault(c.archetype_key, []).append(c)
    return out


def recommend(session, festival_id: int, prof: WeightProfile, top_k: int = 10):
    """Подбор: карточки дневных маршрутов, сгруппированные по архетипам и ранжированные."""
    from figaro.domain.models import (Archetype, Author, Composition,
                                      ConcertComposition, DayRoute,
                                      DayRouteConcert)
    from sqlmodel import select

    from figaro.services import availability

    arche = {a.id: a.key for a in session.exec(
        select(Archetype).where(Archetype.festival_id == festival_id)).all()}
    cards = []
    for dr in session.exec(select(DayRoute).where(DayRoute.festival_id == festival_id)).all():
        if not availability.route_available(session, dr.id):
            continue  # шов наличия: распроданные маршруты не попадают в подбор
        concert_ids = [link.concert_id for link in session.exec(
            select(DayRouteConcert).where(DayRouteConcert.day_route_id == dr.id)).all()]
        authors = set()
        for cid in concert_ids:
            authors |= set(session.exec(select(Author.name).where(
                Author.id == Composition.author_id,
                Composition.id == ConcertComposition.composition_id,
                ConcertComposition.concert_id == cid)).all())
        cards.append(RouteCard(
            id=dr.id, archetype_key=arche.get(dr.archetype_id, "other"),
            concerts_count=dr.concerts_count, days=1,
            transition_minutes=dr.transition_minutes, wait_minutes=dr.wait_minutes,
            cost_kopecks=dr.cost_kopecks, comfort_score=dr.comfort_score,
            diversity_score=dr.diversity_score, authors=frozenset(authors),
            key_authors=tuple(sorted(authors))[:3]))
    grouped = group_by_archetype(cards)
    return {key: rank_cards(group, prof)[:top_k] for key, group in grouped.items()}


# ============ персистентность анкеты (этап 3-веб): UserPreferences ↔ WeightProfile ============
def save_preferences(session, *, user_id: int, festival_id: int,
                     pace: Optional[str] = None, interest_vector: Optional[str] = None,
                     available_days=(), time_windows=(),
                     favorite_author_ids=(), favorite_genre_ids=()):
    """Сохранить/обновить анкету пользователя в рамках фестиваля (upsert по составному ключу)."""
    from figaro.domain.models import UserPreferences

    prefs = session.get(UserPreferences, (user_id, festival_id))
    if prefs is None:
        prefs = UserPreferences(user_id=user_id, festival_id=festival_id)
    prefs.pace = _PACE.get((pace or "").strip().lower())
    prefs.interest_vector = _INTEREST.get((interest_vector or "").strip().lower())
    prefs.available_days = [int(d) for d in available_days]
    prefs.time_windows = list(time_windows)
    prefs.favorite_author_ids = [int(a) for a in favorite_author_ids]
    prefs.favorite_genre_ids = [int(g) for g in favorite_genre_ids]
    session.add(prefs)
    session.flush()
    return prefs


def load_prefs(session, user_id: int, festival_id: int) -> Optional[Prefs]:
    """Прочитать анкету и собрать Prefs (id любимых авторов/жанров → имена для бонуса)."""
    from sqlmodel import select

    from figaro.domain.models import Author, Genre, UserPreferences

    p = session.get(UserPreferences, (user_id, festival_id))
    if p is None:
        return None
    authors = {a.name for a in session.exec(select(Author).where(
        Author.id.in_(p.favorite_author_ids or [-1]))).all()}
    genres = {g.name for g in session.exec(select(Genre).where(
        Genre.id.in_(p.favorite_genre_ids or [-1]))).all()}
    return Prefs(pace=p.pace, interest_vector=p.interest_vector,
                 available_days=tuple(p.available_days or ()),
                 time_windows=tuple(p.time_windows or ()),
                 favorite_authors=frozenset(authors), favorite_genres=frozenset(genres))


def profile_for_user(session, user_id: int, festival_id: int) -> WeightProfile:
    """Веса подбора по сохранённой анкете; если анкеты нет — дефолтные веса."""
    prefs = load_prefs(session, user_id, festival_id)
    return weights_from(prefs or Prefs())


def relax_by_concert_count(cards, target_min: int, target_max: int):
    """Релаксация: если в [min,max] пусто — расширяем диапазон, пока не появятся варианты.
    Возвращает (cards, relaxed: bool). Дни/наличие НЕ ослабляем (это делается раньше/отдельно)."""
    lo, hi, relaxed = target_min, target_max, False
    while lo >= 0 or hi <= 99:
        sel = [c for c in cards if lo <= c.concerts_count <= hi]
        if sel:
            return sel, relaxed
        lo = max(0, lo - 1)
        hi = min(99, hi + 1)
        relaxed = True
        if lo == 0 and hi == 99:
            return [c for c in cards], True
    return [], True
