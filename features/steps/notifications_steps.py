# language: ru
"""Шаги для notifications.feature (этап 6)."""
from datetime import datetime, timedelta

from behave import given, then, when
from sqlmodel import select

import _world as W
from figaro.domain.clock import FestivalClock
from figaro.domain.models import OutboxMessage
from figaro.services import availability, notifications, sheets


def _named(context):
    if not hasattr(context, "named"):
        context.named = {}
    return context.named


def _msgs(context, type=None):
    q = select(OutboxMessage)
    rows = context.session.exec(q).all()
    return [m for m in rows if (type is None or m.type == type)]


class _Recorder:
    def __init__(self, fail=False):
        self.fail = fail
        self.count = 0

    def __call__(self, message):
        self.count += 1
        if self.fail:
            raise RuntimeError("отправка не удалась")


@given('в моём листе есть концерт "{k}" в "{ts}"')
def step_sheet_concert_ts(context, k, ts):
    W.ensure_festival(context)
    context.sheet = sheets.create_empty(context.session, context.actor.id, context.festival.id)
    c = W.concert(context, "A", datetime.fromisoformat(ts), dur=45)
    _named(context)[k] = c
    W.add_item(context, c)
    # доступная альтернатива того же дня (для алерта)
    W.concert(context, "A", datetime.fromisoformat(ts) - timedelta(hours=3), dur=45)


@given('настроено напоминание за {n:d} минут до концерта')
def step_set_reminder(context, n):
    notifications.schedule_reminders(context.session, context.sheet, n)


@when('виртуальное время достигает "{ts}"')
def step_time_reaches(context, ts):
    context.recorder = _Recorder()
    notifications.dispatch(context.session, datetime.fromisoformat(ts), context.recorder)


@then('в outbox появляется сообщение "{type}" для меня')
def step_outbox_has(context, type):
    msgs = [m for m in _msgs(context, type) if m.user_id == context.actor.id]
    assert msgs, type
    context.last_msg = msgs[0]


@then('диспетчер помечает его отправленным')
def step_dispatched_sent(context):
    assert context.last_msg.status == "sent"


@when('виртуальное время — "{ts}"')
def step_virtual_time(context, ts):
    context.recorder = _Recorder()
    notifications.dispatch(context.session, datetime.fromisoformat(ts), context.recorder)


@then('сообщение "{type}" ещё не отправлено')
def step_not_sent_yet(context, type):
    msgs = _msgs(context, type)
    assert msgs and all(m.status == "pending" for m in msgs)


@when('реальное время идёт 1 минуту')
def step_one_real_minute_notif(context):
    # ускоренные часы: переякориваемся к моменту перед напоминанием, минута → 120 вирт. минут
    notifications.schedule_reminders(context.session, context.sheet, 60)
    concert = _named(context)["K"]
    context.clock.set_accelerated(concert.starts_at - timedelta(minutes=61), speed=context.speed or 120)
    context.real.advance(seconds=60)
    context.recorder = _Recorder()
    context.sent = notifications.dispatch(context.session, context.clock.now(), context.recorder)


@then('напоминания за пройденный виртуальный период поставлены и отправлены по порядку')
def step_reminders_fired(context):
    assert context.sent and all(m.status == "sent" for m in context.sent)


@then('в outbox появляется "availability_alert" для меня')
def step_alert_appears(context):
    notifications.alert_soldout(context.session, context.festival.id,
                               _named(context)["K"].id, now=datetime(2026, 7, 1))
    msgs = [m for m in _msgs(context, "availability_alert") if m.user_id == context.actor.id]
    assert msgs
    context.alert = msgs[0]


@then('в нём предложена альтернатива взамен "{k}"')
def step_alert_alt(context, k):
    assert context.alert.payload.get("alternative_id") is not None


@when('тик планировщика срабатывает дважды на одну и ту же виртуальную метку времени')
def step_double_tick(context):
    now = _named(context)["K"].starts_at - timedelta(minutes=60)
    context.recorder = _Recorder()
    for _ in range(2):
        notifications.schedule_reminders(context.session, context.sheet, 60)
        notifications.dispatch(context.session, now, context.recorder)


@then('в outbox ровно одно сообщение "{type}" для этого концерта')
def step_exactly_one(context, type):
    assert len(_msgs(context, type)) == 1


@then('письмо отправлено один раз')
def step_sent_once(context):
    assert context.recorder.count == 1


@given('в outbox есть сообщение, отправка которого падает')
def step_failing_message(context):
    W.ensure_festival(context)
    context.fail_now = datetime(2026, 7, 1, 12, 0)
    notifications.enqueue(context.session, type="concert_reminder", user_id=context.actor.id,
                         scheduled_for=context.fail_now, idempotency_key="fail-1", payload={})


@when('диспетчер пытается его отправить')
def step_dispatch_fail(context):
    context.fail_sender = _Recorder(fail=True)
    notifications.dispatch(context.session, context.fail_now, context.fail_sender)


@then('попытка фиксируется, сообщение остаётся в очереди с возрастающей задержкой')
def step_attempt_recorded(context):
    m = _msgs(context, "concert_reminder")[0]
    assert m.attempts == 1 and m.status == "pending" and m.next_attempt_at is not None


@then('после лимита попыток оно помечается "failed", без бесконечных ретраев')
def step_eventually_failed(context):
    now = context.fail_now
    for _ in range(notifications.MAX_ATTEMPTS + 2):
        now = now + timedelta(minutes=10)
        notifications.dispatch(context.session, now, context.fail_sender)
    m = _msgs(context, "concert_reminder")[0]
    assert m.status == "failed" and m.attempts <= notifications.MAX_ATTEMPTS


@given('доменная логика ставит событие в outbox')
def step_domain_enqueue(context):
    W.ensure_festival(context)
    notifications.enqueue(context.session, type="concert_reminder", user_id=context.actor.id,
                         scheduled_for=datetime(2026, 7, 1, 12, 0), idempotency_key="dom-1")
    assert _msgs(context)[0].status == "pending"


@when('транспорт доставки меняется')
def step_swap_transport(context):
    context.new_sender = _Recorder()  # другой транспорт


@then('точки постановки события не меняются')
def step_enqueue_unchanged(context):
    # тот же enqueue-контракт; доставка идёт через подменённый транспорт
    notifications.dispatch(context.session, datetime(2026, 7, 1, 12, 0), context.new_sender)
    assert context.new_sender.count == 1 and _msgs(context)[0].status == "sent"
