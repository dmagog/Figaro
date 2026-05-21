from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from figaro.db import make_test_engine
from figaro.domain.models import OutboxMessage
from figaro.services import notifications as N

T0 = datetime(2026, 7, 1, 12, 0)


@pytest.fixture
def session():
    with Session(make_test_engine()) as s:
        yield s


def _enqueue(s, key="k1", when=T0):
    return N.enqueue(s, type="concert_reminder", user_id=1, scheduled_for=when,
                     idempotency_key=key)


def test_enqueue_idempotent(session):
    _enqueue(session)
    _enqueue(session)
    assert len(session.exec(select(OutboxMessage)).all()) == 1


def test_dispatch_sends_due(session):
    _enqueue(session, when=T0)
    sent = N.dispatch(session, T0)
    assert len(sent) == 1 and sent[0].status == "sent"


def test_dispatch_not_before(session):
    _enqueue(session, when=T0 + timedelta(hours=1))
    sent = N.dispatch(session, T0)
    assert sent == []
    assert session.exec(select(OutboxMessage)).first().status == "pending"


def test_failing_sender_eventually_failed(session):
    _enqueue(session, when=T0)

    def boom(m):
        raise RuntimeError("fail")

    now = T0
    for _ in range(N.MAX_ATTEMPTS + 2):
        N.dispatch(session, now, boom)
        now += timedelta(minutes=10)
    m = session.exec(select(OutboxMessage)).first()
    assert m.status == "failed" and m.attempts <= N.MAX_ATTEMPTS
