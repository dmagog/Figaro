from datetime import datetime, timedelta

import pytest
from sqlmodel import Session

from figaro.db import make_test_engine
from figaro.services import auth

NOW = datetime(2026, 1, 1)  # naive UTC (см. auth._now)


@pytest.fixture
def session():
    with Session(make_test_engine()) as s:
        yield s


def test_password_roundtrip():
    h = auth.hash_password("secret")
    assert auth.verify_password("secret", h) and not auth.verify_password("nope", h)


def test_register_requires_consent(session):
    with pytest.raises(auth.ConsentRequired):
        auth.register(session, email="a@e.com", password="pw", consent=False)
    u = auth.register(session, email="a@e.com", password="pw", consent=True, now=NOW)
    assert u.consent_at == NOW


def test_lockout(session):
    auth.register(session, email="a@e.com", password="pw", consent=True)
    for _ in range(auth.LOCK_THRESHOLD):
        with pytest.raises(auth.AuthError):
            auth.authenticate(session, email="a@e.com", password="bad", now=NOW)
    with pytest.raises(auth.AccountLocked):
        auth.authenticate(session, email="a@e.com", password="pw", now=NOW)


def test_reset_ttl(session):
    auth.register(session, email="a@e.com", password="pw", consent=True)
    tok = auth.request_password_reset(session, "a@e.com", ttl_minutes=60, now=NOW)
    with pytest.raises(auth.AuthError):
        auth.reset_password(session, tok, "new", now=NOW + timedelta(minutes=61))
    auth.reset_password(session, tok, "new2", now=NOW + timedelta(minutes=10))
    assert auth.authenticate(session, email="a@e.com", password="new2")


def test_rbac_matrix():
    assert auth.can_access("user", "маршрутный лист")
    assert not auth.can_access("user", "пульт эмуляции")
    assert auth.can_access("admin", "пульт эмуляции")
    assert auth.can_access("researcher", "дашборды")
    assert not auth.can_access("researcher", "управление пользователями")


def test_session_logout_expiry(session):
    u = auth.register(session, email="a@e.com", password="pw", consent=True)
    tok = auth.create_session(session, u, now=NOW)
    assert auth.user_for_session(session, tok, now=NOW) is not None
    auth.logout(session, tok)
    assert auth.user_for_session(session, tok, now=NOW) is None
