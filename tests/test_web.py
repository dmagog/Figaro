"""Тонкие @web smoke-тесты: проводка HTTP↔домен (вход, подбор, лист).

Доменное поведение покрыто BDD/юнитами; здесь — что эндпоинты рендерят и
вызывают сервисы, работают cookie-сессия и CSRF.
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from figaro.db import make_test_engine
from figaro.domain.models import (Archetype, AvailabilitySnapshot, Concert,
                                  DayRoute, DayRouteConcert, FestivalDay, Hall)
from figaro.services import auth
from figaro.services.festival import create_festival
from figaro.web.app import create_app

PW = "figaro12345"


def _login_as(client, email):
    client.get("/login")
    csrf = client.cookies.get("figaro_csrf")
    return client.post("/login", data={"email": email, "password": PW, "csrf": csrf},
                       follow_redirects=False)


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
    # длинный маршрут того же архетипа — для проверки влияния темпа анкеты
    dr_long = DayRoute(festival_id=f.id, festival_day_id=day.id, archetype_id=arch.id,
                       concerts_count=8, comfort_score=0.3, diversity_score=0.9, cost_kopecks=900000)
    s.add(dr_long)
    u = auth.register(s, email="u@figaro.dev", password=PW, consent=True)
    u.email_verified = True
    s.add(u)
    admin = auth.register(s, email="admin@figaro.dev", password=PW, consent=True)
    admin.email_verified = True
    admin.role = "admin"
    s.add(admin)
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


def test_questionnaire_pace_changes_recommendations(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    _login(client)

    # дефолт (без анкеты): подсказка заполнить анкету; баланс (target 5) скрывает маршрут на 8
    rec = client.get("/recommend")
    assert "Заполнить анкету" in rec.text
    assert "2 концерт" in rec.text and "8 концерт" not in rec.text

    # марафон — длинные маршруты остаются
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/questionnaire", data={"csrf": csrf, "pace": "marathon"},
                    follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/recommend"
    rec = client.get("/recommend")
    assert "настроено по вашей анкете" in rec.text
    assert "8 концерт" in rec.text and "2 концерт" in rec.text

    # расслабленно — длинный маршрут (8) отфильтрован, короткий (2) остаётся
    csrf = client.cookies.get("figaro_csrf")
    client.post("/questionnaire", data={"csrf": csrf, "pace": "relaxed"})
    rec = client.get("/recommend")
    assert "2 концерт" in rec.text and "8 концерт" not in rec.text


def test_questionnaire_get_renders(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    _login(client)
    r = client.get("/questionnaire")
    assert r.status_code == 200 and "Анкета" in r.text and "Марафон" in r.text


def test_register_requires_consent(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    client.get("/register")
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/register", data={"email": "new@figaro.dev", "password": PW, "csrf": csrf})
    assert r.status_code == 200 and "согласие" in r.text.lower()


def test_register_verify_then_login(app_world):
    import re
    app, _, _ = app_world
    client = TestClient(app)
    client.get("/register")
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/register", data={"email": "new@figaro.dev", "password": PW,
                                       "name": "Новый", "consent": "on", "csrf": csrf})
    assert r.status_code == 200 and "Аккаунт создан" in r.text
    m = re.search(r"/verify\?token=([\w\-]+)", r.text)
    assert m
    # до верификации логин уже работает (домен не блокирует), но проверим саму верификацию
    v = client.get(f"/verify?token={m.group(1)}")
    assert v.status_code == 200 and "подтверждена" in v.text.lower()
    # новый аккаунт может войти
    assert _login_as(client, "new@figaro.dev").status_code == 303


def test_register_duplicate_email(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    client.get("/register")
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/register", data={"email": "u@figaro.dev", "password": PW,
                                       "consent": "on", "csrf": csrf})
    assert r.status_code == 200 and "занят" in r.text.lower()


def test_pult_requires_admin(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    _login_as(client, "u@figaro.dev")  # роль user
    assert client.get("/admin/pult").status_code == 403


def test_pult_admin_can_set_clock(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    _login_as(client, "admin@figaro.dev")
    page = client.get("/admin/pult")
    assert page.status_code == 200 and "Пульт эмуляции" in page.text

    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/admin/pult/clock",
                    data={"csrf": csrf, "mode": "offset", "virtual": "2026-07-01T12:00"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert app.state.clock.mode.value == "offset"
    assert app.state.clock.now().date().isoformat() == "2026-07-01"
    assert "offset" in client.get("/admin/pult").text


def test_pult_availability_recompute_writes_snapshots(app_world):
    app, _, _ = app_world
    client = TestClient(app)
    _login_as(client, "admin@figaro.dev")
    csrf = client.cookies.get("figaro_csrf")
    r = client.post("/admin/pult/availability",
                    data={"csrf": csrf, "mode": "sim_curve", "seed": "7"},
                    follow_redirects=False)
    assert r.status_code == 303
    with Session(app.state.engine) as s:
        snaps = s.exec(select(AvailabilitySnapshot)).all()
    assert len(snaps) == 3 and all(sn.source == "sim_curve" for sn in snaps)
