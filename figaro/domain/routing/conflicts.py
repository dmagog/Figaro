"""Оценка перехода между концертами (docs/03-route-engine.md#правила-конфликтов).

Резолв walk: матрица → оценка по координатам (walk_speed) → None.
Пороги — из конфигурации (не хардкод, урок v2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Hashable, Optional, Tuple


class Status(str, Enum):
    OK = "ok"
    TIGHT = "tight"
    HURRY = "hurry"
    OVERLAP = "overlap"
    SAME_HALL = "same_hall"
    SAME_BUILDING = "same_building"
    NO_DATA = "no_data"


PASSABLE = {Status.OK, Status.TIGHT, Status.SAME_HALL, Status.SAME_BUILDING}


@dataclass
class TransitionConfig:
    buffer_tight_minutes: int = 10
    buffer_overlap_slack: int = 3
    walk_speed_m_per_min: float = 83.3


def _haversine_m(c1: Tuple[float, float], c2: Tuple[float, float]) -> float:
    r = 6_371_000.0
    lat1, lon1, lat2, lon2 = map(math.radians, (c1[0], c1[1], c2[0], c2[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _has_coords(c: Optional[Tuple[Optional[float], Optional[float]]]) -> bool:
    return bool(c) and c[0] is not None and c[1] is not None and not (c[0] == 0 and c[1] == 0)


class TransitionResolver:
    """Хранит матрицу переходов и координаты залов; отдаёт время перехода в минутах."""

    def __init__(self, matrix: Dict[Tuple[Hashable, Hashable], int],
                 coords: Optional[Dict[Hashable, Tuple[float, float]]] = None,
                 config: Optional[TransitionConfig] = None):
        self.matrix = dict(matrix)
        self.coords = coords or {}
        self.cfg = config or TransitionConfig()

    def walk(self, a: Hashable, b: Hashable) -> Optional[int]:
        if a == b:
            return 0
        if (a, b) in self.matrix:
            return self.matrix[(a, b)]
        if (b, a) in self.matrix:
            return self.matrix[(b, a)]
        ca, cb = self.coords.get(a), self.coords.get(b)
        if _has_coords(ca) and _has_coords(cb):
            return round(_haversine_m(ca, cb) / self.cfg.walk_speed_m_per_min)
        return None


def evaluate(prev_end: datetime, next_start: datetime, prev_hall: Hashable,
             next_hall: Hashable, walk_minutes: Optional[int],
             cfg: Optional[TransitionConfig] = None) -> Status:
    cfg = cfg or TransitionConfig()
    gap = (next_start - prev_end).total_seconds() / 60.0
    if gap < 0:
        return Status.OVERLAP
    if prev_hall == next_hall or walk_minutes == 0:
        return Status.SAME_HALL
    if walk_minutes is None:
        return Status.NO_DATA
    if walk_minutes == 1:
        return Status.SAME_BUILDING
    if gap < walk_minutes - cfg.buffer_overlap_slack:
        return Status.OVERLAP
    if gap < walk_minutes:
        return Status.HURRY
    if gap < walk_minutes + cfg.buffer_tight_minutes:
        return Status.TIGHT
    return Status.OK
