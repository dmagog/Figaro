"""Аутентификация, RBAC, безопасность, приватность (этап 3, docs/08).

Время для auth (TTL токенов/сессий, lockout) — реальное, инъектируется (`now`)
для детерминизма тестов. Это не festival-время (FestivalClock — отдельно).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import Session, select

from figaro.domain.models import (AuthToken, RouteSheet, RouteSheetItem,
                                  User, UserPreferences, UserSession)

LOCK_THRESHOLD = 5
LOCK_MINUTES = 15
_PBKDF2_ITERS = 100_000


class ConsentRequired(Exception):
    pass


class AccountLocked(Exception):
    pass


class AuthError(Exception):
    pass


class CsrfError(Exception):
    pass


class Forbidden(Exception):
    pass


def _now() -> datetime:
    # naive UTC — согласовано с хранением datetime в БД (sqlite/Postgres TIMESTAMP)
    return datetime.utcnow()


# --- пароли (pbkdf2, stdlib) ---
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _PBKDF2_ITERS)
    return f"pbkdf2${_PBKDF2_ITERS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, h = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), h)
    except Exception:
        return False


# --- регистрация / верификация ---
def register(session: Session, *, email: str, password: str, name: Optional[str] = None,
             consent: bool, marketing: bool = False, now: Optional[datetime] = None) -> User:
    now = now or _now()
    if not consent:
        raise ConsentRequired("требуется согласие на обработку ПДн")
    if session.exec(select(User).where(User.email == email)).first():
        raise AuthError("email уже занят")
    u = User(email=email, name=name, hashed_password=hash_password(password),
             role="user", consent_at=now, marketing_consent=marketing)
    session.add(u)
    session.flush()
    return u


def issue_token(session: Session, user: User, kind: str, ttl_minutes: int,
                now: Optional[datetime] = None) -> str:
    now = now or _now()
    tok = secrets.token_urlsafe(24)
    session.add(AuthToken(user_id=user.id, kind=kind, token=tok,
                          expires_at=now + timedelta(minutes=ttl_minutes)))
    session.flush()
    return tok


def request_email_verification(session, user, now=None) -> str:
    return issue_token(session, user, "verify", 60 * 24, now)


def verify_email(session: Session, token: str, now: Optional[datetime] = None) -> User:
    now = now or _now()
    at = session.exec(select(AuthToken).where(
        AuthToken.token == token, AuthToken.kind == "verify")).first()
    if not at or at.used or at.expires_at < now:
        raise AuthError("неверный или просроченный токен верификации")
    u = session.get(User, at.user_id)
    u.email_verified = True
    at.used = True
    session.add(u)
    session.add(at)
    session.flush()
    return u


# --- вход / lockout ---
def authenticate(session: Session, *, email: str, password: str,
                 now: Optional[datetime] = None) -> User:
    now = now or _now()
    u = session.exec(select(User).where(User.email == email)).first()
    if not u:
        raise AuthError("нет такого пользователя")
    if u.locked_until and u.locked_until > now:
        raise AccountLocked("временно заблокировано из-за множества неудачных попыток")
    if not verify_password(password, u.hashed_password):
        u.failed_login_count += 1
        if u.failed_login_count >= LOCK_THRESHOLD:
            u.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        session.add(u)
        session.flush()
        raise AuthError("неверный пароль")
    u.failed_login_count = 0
    u.locked_until = None
    session.add(u)
    session.flush()
    return u


# --- сброс пароля ---
def request_password_reset(session, email, ttl_minutes=60, now=None) -> Optional[str]:
    u = session.exec(select(User).where(User.email == email)).first()
    if not u:
        return None
    return issue_token(session, u, "reset", ttl_minutes, now)


def reset_password(session: Session, token: str, new_password: str,
                   now: Optional[datetime] = None) -> User:
    now = now or _now()
    at = session.exec(select(AuthToken).where(
        AuthToken.token == token, AuthToken.kind == "reset")).first()
    if not at or at.used or at.expires_at < now:
        raise AuthError("неверный или просроченный токен сброса")
    u = session.get(User, at.user_id)
    u.hashed_password = hash_password(new_password)
    u.failed_login_count = 0
    u.locked_until = None
    at.used = True
    session.add(u)
    session.add(at)
    session.flush()
    return u


# --- сессии ---
def create_session(session, user, ttl_minutes=60 * 24, now=None) -> str:
    now = now or _now()
    tok = secrets.token_urlsafe(24)
    session.add(UserSession(user_id=user.id, token=tok,
                            expires_at=now + timedelta(minutes=ttl_minutes)))
    session.flush()
    return tok


def user_for_session(session, token, now=None) -> Optional[User]:
    now = now or _now()
    s = session.exec(select(UserSession).where(UserSession.token == token)).first()
    if not s or s.revoked or s.expires_at < now:
        return None
    return session.get(User, s.user_id)


def logout(session, token) -> None:
    s = session.exec(select(UserSession).where(UserSession.token == token)).first()
    if s:
        s.revoked = True
        session.add(s)
        session.flush()


# --- RBAC ---
ACCESS = {
    "маршрутный лист": {"user", "researcher", "admin"},
    "подбор маршрутов": {"user", "researcher", "admin"},
    "дашборды": {"researcher", "admin"},
    "управление пользователями": {"admin"},
    "пульт эмуляции": {"admin"},
    "запуск пересчёта маршрутов": {"admin"},
}


def can_access(role: str, area: str) -> bool:
    return role in ACCESS.get(area, set())


def change_role(session: Session, *, actor: User, target_email: str, new_role: str) -> User:
    if actor.role != "admin":
        raise Forbidden("сменить роль может только admin")
    u = session.exec(select(User).where(User.email == target_email)).first()
    if not u:
        raise AuthError("нет такого пользователя")
    u.role = new_role
    session.add(u)
    session.flush()
    return u


# --- CSRF / владение ---
def verify_csrf(token: Optional[str], expected: Optional[str]) -> None:
    if not token or not expected or not hmac.compare_digest(str(token), str(expected)):
        raise CsrfError("403")


def assert_can_edit_sheet(user_id: int, sheet: RouteSheet) -> None:
    if sheet.user_id != user_id:
        raise Forbidden("403")


# --- приватность ---
def delete_account(session: Session, user_id: int) -> None:
    """Право на удаление: убираем аккаунт и связанные ПДн."""
    for sheet in session.exec(select(RouteSheet).where(RouteSheet.user_id == user_id)).all():
        for it in session.exec(select(RouteSheetItem).where(
                RouteSheetItem.route_sheet_id == sheet.id)).all():
            session.delete(it)
        session.delete(sheet)
    for model in (UserPreferences, AuthToken, UserSession):
        for row in session.exec(select(model).where(model.user_id == user_id)).all():
            session.delete(row)
    u = session.get(User, user_id)
    if u:
        session.delete(u)
    session.flush()


def researcher_customer_aggregates(session: Session):
    """Псевдонимизированная аналитика: только псевдонимы покупателей и счётчики, без ПДн."""
    from figaro.domain.models import Purchase
    counts = {}
    for p in session.exec(select(Purchase)).all():
        counts[p.customer_external_id] = counts.get(p.customer_external_id, 0) + 1
    return [{"customer": cid, "purchases": n} for cid, n in counts.items()]
