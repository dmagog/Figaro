"""behave-хуки: изолированное состояние и управляемые часы на каждый сценарий.
Время — только через FestivalClock с фиктивным real_now (детерминизм, ADR 0005)."""
import os
import sys
from datetime import date, datetime, timedelta, timezone

# repo root → чтобы импортировался пакет figaro
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from figaro.domain.clock import FestivalClock  # noqa: E402


class FakeReal:
    """Управляемое «реальное» время для детерминированных сценариев."""

    def __init__(self, t: datetime):
        self.t = t

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t = self.t + timedelta(**kw)


def before_scenario(context, scenario):
    context.real = FakeReal(datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc))
    context.clock = FestivalClock(real_now=context.real)
    # значения по умолчанию (Background/шаги могут переопределить)
    context.sales_start = date(2026, 6, 1)
    context.festival_start = date(2026, 7, 1)
    context.festival_end = date(2026, 7, 3)
    context.speed = 1.0
    context.virtual_anchor = None
    context.result = None
    context.result_date = None
