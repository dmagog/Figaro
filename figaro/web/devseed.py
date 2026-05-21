"""Демо-сидинг для локального запуска веб-слоя: активный фестиваль + демо-пользователи.

Операторский путь (вне автотестов): импортирует реальный каталог из Excel,
делает предрасчёт маршрутов и активирует фестиваль, плюс заводит демо-аккаунты
для упрощённого входа.

Пример:
    DATABASE_URL="sqlite:///instance/figaro_dev.db" \
        ./.venv/bin/python -m figaro.web.devseed --data-dir data
    ./.venv/bin/uvicorn figaro.web.app:app --port 8731
"""
from __future__ import annotations

import argparse
from datetime import date

from sqlmodel import SQLModel, select

from figaro.batch.precompute import precompute_festival
from figaro.config import settings
from figaro.db import make_engine, session_scope
from figaro.domain.models import Festival, User
from figaro.importing.seed import import_catalog
from figaro.importing.source import from_excel
from figaro.services import auth
from figaro.services.festival import activate, create_festival

DEMO_PASSWORD = "figaro12345"
DEMO_USERS = [("user@figaro.dev", "user"),
              ("researcher@figaro.dev", "researcher"),
              ("admin@figaro.dev", "admin")]


def ensure_users(session):  # pragma: no cover - операторский путь
    for email, role in DEMO_USERS:
        u = session.exec(select(User).where(User.email == email)).first()
        if u is None:
            u = auth.register(session, email=email, password=DEMO_PASSWORD, consent=True)
        u.email_verified = True
        u.role = role
        session.add(u)
    session.flush()


def seed(session, data_dir: str = "data", *, name: str = "Безумные дни 2022",
         year: int = 2022, sales_start: date = date(2022, 6, 1),
         start: date = date(2022, 7, 1), end: date = date(2022, 7, 3)):  # pragma: no cover
    ensure_users(session)
    fest = session.exec(select(Festival).where(Festival.year == year)).first()
    if fest is None:
        fest = create_festival(session, name=name, year=year, sales_start_on=sales_start,
                               starts_on=start, ends_on=end)
        src = from_excel(data_dir)
        src.purchases = []  # даты покупок в реальной выгрузке требуют аудита (docs/05);
                            # для демо-подбора и листа они не нужны (наличие отложено)
        import_catalog(session, fest.id, src)
        precompute_festival(session, fest.id)
    if fest.status != "active":
        activate(session, fest.id)
    return fest


def main() -> None:  # pragma: no cover - операторский путь
    p = argparse.ArgumentParser(description="Демо-сидинг веб-слоя (фестиваль + пользователи)")
    p.add_argument("--data-dir", default="data")
    args = p.parse_args()
    engine = make_engine(settings.database_url)
    if engine.url.get_backend_name() == "sqlite":
        SQLModel.metadata.create_all(engine)
    with session_scope(engine) as s:
        fest = seed(s, args.data_dir)
        print(f"active festival #{fest.id} '{fest.name}'; "
              f"демо-вход: user@figaro.dev / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
