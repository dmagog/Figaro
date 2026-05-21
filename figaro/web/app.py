"""Точка входа FastAPI (server-rendered + HTMX, ADR 0001).

Веб-слой: упрощённый вход, анкета, подбор маршрутов, маршрутный лист и
админский пульт эмуляции (FestivalClock + наличие). Доменная логика — в
services/*, веб лишь её показывает.

Запуск: `uvicorn figaro.web.app:app`. Движок БД берётся из settings.database_url
(резолвится на старте, чтобы импорт модуля не требовал драйвера БД); для sqlite-dev
таблицы создаются на старте, в Postgres схему ведёт Alembic. FestivalClock хранится
на app.state и (если задан clock_path) переживает рестарт.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import SQLModel

from figaro import __version__
from figaro.config import settings
from figaro.db import make_engine
from figaro.domain.clock import FestivalClock
from figaro.services import auth
from figaro.web.routes import router


def _init_sqlite(engine) -> None:
    if engine.url.get_backend_name() == "sqlite":
        SQLModel.metadata.create_all(engine)  # dev-режим; в Postgres схему ведёт Alembic


def create_app(engine: Optional[object] = None, clock_path: Optional[str] = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.engine is None:  # дефолтный движок резолвим на старте, не при импорте
            app.state.engine = make_engine(settings.database_url)
            _init_sqlite(app.state.engine)
        if clock_path and Path(clock_path).exists():  # восстановить часы после рестарта
            app.state.clock = FestivalClock.load(clock_path)
        yield

    app = FastAPI(title="Figaro v3", version=__version__, lifespan=lifespan)
    app.state.engine = engine
    app.state.clock = FestivalClock()       # по умолчанию — реальное время, в памяти
    app.state.clock_path = clock_path        # None → пульт не пишет на диск (тесты чисты)
    if engine is not None:
        _init_sqlite(engine)
    app.include_router(router)

    @app.exception_handler(auth.CsrfError)
    def _csrf_handler(request: Request, exc: auth.CsrfError):
        return PlainTextResponse("403 — неверный CSRF-токен", status_code=403)

    @app.exception_handler(auth.Forbidden)
    def _forbidden_handler(request: Request, exc: auth.Forbidden):
        return PlainTextResponse("403 — доступ запрещён", status_code=403)

    return app


app = create_app(clock_path=settings.clock_state_path)
