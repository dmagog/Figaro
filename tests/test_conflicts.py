from datetime import datetime

import pytest

from figaro.domain.routing.conflicts import (Status, TransitionConfig,
                                             TransitionResolver, evaluate)

CFG = TransitionConfig(buffer_tight_minutes=10, buffer_overlap_slack=3)
RESOLVER = TransitionResolver(
    matrix={("A", "B"): 15, ("A", "C"): 0, ("A", "E"): 1},
    coords={"F": (56.838, 60.597), "G": (56.842, 60.601)},
    config=CFG,
)


def _at(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return datetime(2026, 7, 1, h, m)


@pytest.mark.parametrize("end,hall,start,expected", [
    ("12:00", "B", "11:50", Status.OVERLAP),
    ("12:00", "B", "12:05", Status.OVERLAP),
    ("12:00", "B", "12:13", Status.HURRY),
    ("12:00", "B", "12:20", Status.TIGHT),
    ("12:00", "B", "12:30", Status.OK),
    ("12:00", "A", "12:05", Status.SAME_HALL),
    ("12:00", "C", "12:01", Status.SAME_HALL),
    ("12:00", "E", "12:02", Status.SAME_BUILDING),
    ("12:00", "D", "12:30", Status.NO_DATA),
])
def test_status_matrix(end, hall, start, expected):
    walk = RESOLVER.walk("A", hall)
    assert evaluate(_at(end), _at(start), "A", hall, walk, CFG) == expected


def test_threshold_from_config():
    cfg = TransitionConfig(buffer_tight_minutes=20, buffer_overlap_slack=3)
    walk = RESOLVER.walk("A", "B")  # 15
    # gap 30 < 15+20 → tight
    assert evaluate(_at("12:00"), _at("12:30"), "A", "B", walk, cfg) == Status.TIGHT


def test_coordinate_estimate():
    walk = RESOLVER.walk("F", "G")  # нет в матрице, есть координаты
    assert walk is not None and walk >= 1
    status = evaluate(_at("12:00"), _at("13:00"), "F", "G", walk, CFG)
    assert status != Status.NO_DATA
