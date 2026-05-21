"""Тонкие @web smoke-тесты: проводка HTTP↔домен (вход, подбор, лист).

Доменное поведение покрыто BDD/юнитами; здесь — что эндпоинты рендерят и
вызывают сервисы, работают cookie-сессия и CSRF.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from figaro.db import make_test_engine
from figaro.domain.models import (Archetype, Concert, DayRoute, DayRouteConcert,
                                  FestivalDay, Hall)
from figaro.services import auth
from figaro.services.festival import create_festival
from figaro.web.app import create_app

PW = "figaro12345"


@pytest.fixture
def app_world():
    engine = make_test_engine()
    s = Session(engine)
    f = create_festival(s, name="2026", year=2026, sales_start_on=date(2026, 6, 1),
                        starts_on=date(2026, 7, 1), ends_on=date(2026, 7, 3))
    f.status = "active"
    s.add(f)
    hall = Hall(festival_id=f.id, name="A", seats=100)
    s.add(hall)
    s.flush()
    day = FestivalDay(festival_id=f.id, day=date(2026, 7, 1))
    s.add(day)
    s.flush()
    c1 = Concert(festival_id=f.id, show_num=1, crm_show_id=1, title="Утренний", hall_id=hall.id,
                 festival_day_id=day.id, starts_at=datetime(2026, 7, 1, 10, 0), duration_min=50, capacity=50)
    c2 = Concert(festival_id=f.id, show_num=2, crm_show_id=2, title="Дневной", hall_id=hall.id,
                 festival_day_id=day.id, starts_at=datetime(2026, 7, 1, 11, 30), duration_min=45, capacity=50)
    c3 = Concert(festival_id=f.id, show_num=3, crm_show_id=3, title="Вечерний", hall_id=hall.id,
                 festival_day_id=day.id, starts_at=datetime(2026, 7, 1, 13, 0), duration_min=50, capacity=50)
    s.add_all([c1, c2, c3])
    s.flush()
    arch = Archetype(festival_id=f.id, key="comfort", title="Комфортный")
    s.add(arch)
    s.flush()
    dr = DayRoute(festival_id=f.id, festival_day_id=day.id, archetype_id=arch.id,
                  concerts_count=2, comfort_score=0.8, diversity_score=0.5, cost_kopecks=500000)
    s.add(dr)
    s.flush()
    s.add(DayRouteConcert(day_route_id=dr.id, concert_id=c1.id, position=0))
    s.add(DayRouteConcert(day_route_id=dr.id, concert_id=c3.id, position=1))
    u = auth.register(s, email="u@figaro.dev", password=PW, consent=True)
    u.email_verified = True
    s.add(u)
    s.commit()
    dr_id, c2_id = dr.id, c2.id  # снимаем id до закрытия сессии (иначе detached)
    s.close()
    app = create_app(engine=engine)
    return app, dr_id, c2_id


def _login(client):
    client.get("/login")  # выставляет csrf-cookie
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/login", data={"email": "u@figaro.dev", "password": PW, "csrf": csrf},
                    follow_redirects=False)
    return r


def test_health(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_root_and_recommend_require_login(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    r = client.get("/recommend", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"


def test_login_wrong_password_shows_error(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    client.get("/login")
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/login", data={"email": "u@figaro.dev", "password": "nope", "csrf": csrf})
    assert r.status_code == 200 and "неверный пароль" in r.text


def test_login_then_recommend_shows_card(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"] == "/recommend"
    assert client.cookies.get("figaro_sid")
    page = client.get("/recommend")
    assert page.status_code == 200
    assert "Комфортный" in page.text and "2 концерт" in page.text


def test_from_route_then_edit_sheet(app_world):
    app, dr_id, c2_id = app_world
    client = TestClient(app)
    _login(client)
    csrf = client.cookies.get("figaro_csrf")
    r = client.post(f"/sheet/from-route/{dr_id}", data={"csrf": csrf}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/sheet?sheet_id=")
    sheet_id = int(r.headers["location"].split("=")[1])

    page = client.get(f"/sheet?sheet_id={sheet_id}")
    assert "Утренний" in page.text and "Вечерний" in page.text
    # дневной концерт помещается в щель → предлагается к добавлению
    assert "Дневной" in page.text

    add = client.post(f"/sheet/{sheet_id}/add/{c2_id}", data={"csrf": csrf})
    assert add.status_code == 200 and "Дневной" in add.text
    # после добавления его уже нет среди подсказок, но он есть в составе листа
    rm = client.post(f"/sheet/{sheet_id}/remove/{c2_id}", data={"csrf": csrf})
    assert rm.status_code == 200


def test_csrf_required_on_post(app_world):
    app, dr_id, _ = app_world
    client = TestClient(app)
    _login(client)
    r = client.post(f"/sheet/from-route/{dr_id}", data={"csrf": "wrong"}, follow_redirects=False)
    assert r.status_code == 403
