# language: ru
"""Шаги для clock.feature (этап 0). Текст шагов — русский, функции — английские."""
import re
import tempfile
from datetime import date, datetime, timedelta, timezone

from behave import given, then, when

from figaro.domain.clock import ClockMode, Phase, phase_for


def _noon(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 12, 0, 0, tzinfo=timezone.utc)


@given('фестиваль идёт с "{start}" по "{end}"')
def step_festival_dates(context, start, end):
    context.festival_start = date.fromisoformat(start)
    context.festival_end = date.fromisoformat(end)


@given('часы в режиме "{mode}"')
def step_clock_mode(context, mode):
    if mode == "real":
        context.clock.set_real()
    elif mode == "offset":
        context.clock.set_offset(context.real())
    else:
        raise AssertionError(f"неожиданный режим: {mode}")


@given('часы в режиме "offset" со сдвигом "{shift}" относительно старта фестиваля')
def step_clock_offset_shift(context, shift):
    m = re.search(r"-?\d+", shift)
    days = int(m.group())
    context.clock.set_offset(_noon(context.festival_start + timedelta(days=days)))


@given('часы в режиме "accelerated" со скоростью {k:d}')
def step_clock_accelerated(context, k):
    context.speed = float(k)
    context.clock.set_accelerated(context.real(), speed=context.speed)


@given('виртуальное время зафиксировано на "{ts}"')
def step_pin_virtual(context, ts):
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    context.virtual_anchor = dt
    context.clock.set_accelerated(dt, speed=context.speed)


@given('старт продаж "{ss}", фестиваль "{fs}".."{fe}"')
def step_sales_and_festival(context, ss, fs, fe):
    context.sales_start = date.fromisoformat(ss)
    context.festival_start = date.fromisoformat(fs)
    context.festival_end = date.fromisoformat(fe)


@when('я запрашиваю текущее время')
def step_query_now(context):
    context.result = context.clock.now()


@when('я запрашиваю текущую виртуальную дату')
def step_query_virtual_date(context):
    context.result_date = context.clock.now().date()


@when('проходит {n:d} реальных секунд')
def step_advance_real(context, n):
    context.real.advance(seconds=n)


@when('администратор переводит виртуальную дату на "{d}"')
def step_jump_to(context, d):
    context.clock.jump_to(_noon(date.fromisoformat(d)))


@when('виртуальная дата — "{d}"')
def step_set_virtual_date(context, d):
    context.clock.set_offset(_noon(date.fromisoformat(d)))


@when('приложение перезапускается')
def step_restart(context):
    from figaro.domain.clock import FestivalClock
    path = tempfile.mktemp(suffix=".json")
    context.clock.save(path)
    context.clock = FestivalClock.load(path, real_now=context.real)


@then('оно совпадает с системным временем')
def step_assert_real(context):
    assert context.result == context.real(), (context.result, context.real())


@then('виртуальная дата равна "{d}"')
def step_assert_virtual_date(context, d):
    assert context.result_date == date.fromisoformat(d), context.result_date


@then('фаза фестиваля — "{phase}"')
def step_assert_phase(context, phase):
    actual = phase_for(context.clock.now().date(), context.sales_start,
                       context.festival_start, context.festival_end)
    assert actual == Phase(phase), (actual, phase)


@then('виртуальное время продвинулось на {m:d} минут')
def step_assert_advanced(context, m):
    delta = context.clock.now() - context.virtual_anchor
    assert delta == timedelta(minutes=m), delta


@then('режим часов остаётся "accelerated" со скоростью {k:d}')
def step_assert_mode(context, k):
    assert context.clock.mode == ClockMode.ACCELERATED, context.clock.mode
    assert context.clock.state.speed == k, context.clock.state.speed
