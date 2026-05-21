"""Веб-инфраструктура: сессия БД на запрос, текущий пользователь, CSRF (double-submit).

Веб-слой намеренно тонкий: вся логика — в services/*, здесь только проводка
HTTP↔домен (ADR 0001 server-rendered + HTMX).
"""
from __future__ import annotations

import secrets
from typing import Iterator, Optional

from fastapi import Depends, Request
from sqlmodel import Session

from figaro.domain.models import User
from figaro.services import auth

SESSION_COOKIE = "figaro_sid"
CSRF_COOKIE = "figaro_csrf"


def get_session(request: Request) -> Iterator[Session]:
    """Сессия БД на запрос: коммит при успехе, откат при ошибке."""
    engine = request.app.state.engine
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def current_user(request: Request,
                 session: Session = Depends(get_session)) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return auth.user_for_session(session, token)


def csrf_token(request: Request) -> str:
    """Текущий CSRF-токен из cookie (или новый — выставляется в ответе через set_csrf_cookie)."""
    return request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(24)


def set_csrf_cookie(response, token: str) -> None:
    # double-submit: значение читается шаблоном (не httponly) и сверяется на POST
    response.set_cookie(CSRF_COOKIE, token, httponly=False, samesite="lax", path="/")


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", path="/")


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
