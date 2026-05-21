"""behave-хуки: изолированное состояние, управляемые часы и чистая БД на каждый сценарий.
Время — только через FestivalClock с фиктивным real_now (детерминизм, ADR 0005).
БД — sqlite in-memory на сценарий (быстро, без Postgres)."""
import os
import sys
from datetime import date, datetime, timedelta, timezone

# repo root → чтобы импортировался пакет figaro; steps/ → чтобы шаги видели _world
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "steps")))

from sqlmodel import Session  # noqa: E402

from figaro.db import make_test_engine  # noqa: E402
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
    # --- часы ---
    context.real = FakeReal(datetime(2026, 6, 30, 12, 0, 0, tzinfo=timezone.utc))
    context.clock = FestivalClock(real_now=context.real)
    context.sales_start = date(2026, 6, 1)
    context.festival_start = date(2026, 7, 1)
    context.festival_end = date(2026, 7, 3)
    context.speed = 1.0
    context.virtual_anchor = None
    context.result = None
    context.result_date = None
    # --- БД ---
    context.engine = make_test_engine()
    context.session = Session(context.engine)
    # --- состояние доменных сценариев ---
    context.festival = None
    context.festivals = {}
    context.src = None


def after_scenario(context, scenario):
    try:
        context.session.close()
    except Exception:
        pass
