from datetime import date, datetime, timedelta, timezone

from figaro.domain.clock import ClockMode, FestivalClock, Phase, phase_for


class FakeReal:
    def __init__(self, t: datetime):
        self.t = t

    def __call__(self) -> datetime:
        return self.t

    def advance(self, **kw) -> None:
        self.t = self.t + timedelta(**kw)


def test_real_mode_returns_system_time():
    fr = FakeReal(datetime(2026, 1, 1, tzinfo=timezone.utc))
    c = FestivalClock(real_now=fr)
    c.set_real()
    assert c.now() == fr.t


def test_offset_shifts_and_advances():
    fr = FakeReal(datetime(2026, 6, 30, 12, tzinfo=timezone.utc))
    c = FestivalClock(real_now=fr)
    c.set_offset(datetime(2026, 6, 17, 12, tzinfo=timezone.utc))
    assert c.now().date() == date(2026, 6, 17)
    fr.advance(days=1)
    assert c.now().date() == date(2026, 6, 18)  # идёт обычной скоростью


def test_accelerated_advances_by_speed():
    fr = FakeReal(datetime(2026, 1, 1, tzinfo=timezone.utc))
    c = FestivalClock(real_now=fr)
    c.set_accelerated(datetime(2026, 7, 1, 10, tzinfo=timezone.utc), speed=60)
    fr.advance(seconds=60)
    assert c.now() == datetime(2026, 7, 1, 11, tzinfo=timezone.utc)  # +60 виртуальных минут


def test_state_survives_restart(tmp_path):
    c = FestivalClock()
    c.set_accelerated(datetime(2026, 7, 1, tzinfo=timezone.utc), speed=60)
    p = tmp_path / "clock_state.json"
    c.save(p)
    c2 = FestivalClock.load(p)
    assert c2.mode == ClockMode.ACCELERATED
    assert c2.state.speed == 60


def test_phases():
    ss, fs, fe = date(2026, 6, 1), date(2026, 7, 1), date(2026, 7, 3)
    assert phase_for(date(2026, 5, 15), ss, fs, fe) == Phase.PRE_SALE
    assert phase_for(date(2026, 6, 10), ss, fs, fe) == Phase.ON_SALE
    assert phase_for(date(2026, 7, 2), ss, fs, fe) == Phase.FESTIVAL
    assert phase_for(date(2026, 7, 10), ss, fs, fe) == Phase.POST
