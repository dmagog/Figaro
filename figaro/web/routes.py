"""HTTP-маршруты веб-слоя (server-rendered + HTMX). Логики нет — только проводка к services/*.

Первый срез: упрощённый вход, подбор маршрутов, редактирование маршрутного листа
(добавить/убрать/закрепить) с подсказками концертов и офф-программы.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from figaro.domain.clock import phase_for
from figaro.domain.models import (Archetype, Author, Concert, Hall, RouteSheet,
                                  RouteSheetItem)
from figaro.services import analytics, auth, availability, sheets
from figaro.services.festival import get_active
from figaro.services.recommend import (load_prefs, profile_for_user,
                                       recommend, relax_by_concert_count,
                                       save_preferences)
from figaro.web.deps import (CSRF_COOKIE, SESSION_COOKIE, clear_session_cookie,
                             csrf_token, current_user, get_session,
                             set_csrf_cookie, set_session_cookie)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
templates.env.filters["rub"] = lambda k: f"{(k or 0) // 100:,} ₽".replace(",", " ")
templates.env.filters["hhmm"] = lambda dt: dt.strftime("%H:%M") if dt else ""
templates.env.filters["dtlocal"] = lambda dt: dt.strftime("%Y-%m-%dT%H:%M") if dt else ""

DEMO_ACCOUNTS = ["user@figaro.dev / figaro12345", "admin@figaro.dev / figaro12345 (пульт)"]


# --- хелперы ---
def _page(request: Request, name: str, user, ctx: dict):
    token = csrf_token(request)
    resp = templates.TemplateResponse(request, name, {"user": user, "csrf": token, **ctx})
    set_csrf_cookie(resp, token)
    return resp


def _verify_csrf(request: Request, form_csrf: Optional[str]) -> None:
    auth.verify_csrf(form_csrf, request.cookies.get(CSRF_COOKIE))


def _concert_disp(session: Session, concert_id: int) -> dict:
    c = session.get(Concert, concert_id)
    h = session.get(Hall, c.hall_id)
    return {"id": c.id, "concert_id": c.id, "title": c.title,
            "hall": h.name if h else "—", "start": c.starts_at,
            "end": c.starts_at + timedelta(minutes=c.duration_min)}


def _sheet_view(session: Session, sheet: RouteSheet) -> dict:
    rows = session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == sheet.id)).all()
    pinned = {r.concert_id: r.is_pinned for r in rows}
    items = []
    for c in sorted((session.get(Concert, r.concert_id) for r in rows),
                    key=lambda c: c.starts_at):
        d = _concert_disp(session, c.id)
        d["pinned"] = pinned.get(c.id, False)
        items.append(d)
    suggestions = []
    for s in sheets.suggest_additions(session, sheet):
        d = _concert_disp(session, s.concert_id)
        d.update(transition_minutes=s.transition_minutes, is_repeat=s.is_repeat)
        suggestions.append(d)
    offprogram = [{"title": o.title, "is_recommended": o.is_recommended,
                   "transition_minutes": o.transition_minutes}
                  for o in sheets.suggest_off_program(session, sheet)]
    # SimpleNamespace, чтобы view.items в шаблоне не коллизировал с dict.items
    return SimpleNamespace(sheet=sheet, items=items, suggestions=suggestions,
                           offprogram=offprogram)


def _sheet_partial(request: Request, session: Session, user, sheet: RouteSheet,
                   notice: Optional[str] = None):
    return _page(request, "_sheet.html", user,
                 {"view": _sheet_view(session, sheet), "notice": notice})


def _owned_sheet(session: Session, sheet_id: int, user) -> RouteSheet:
    sheet = session.get(RouteSheet, sheet_id)
    if sheet is None:
        raise HTTPException(404)
    auth.assert_can_edit_sheet(user.id, sheet)
    return sheet


# --- корень / health ---
@router.get("/health")
def health() -> dict:
    from figaro import __version__
    return {"status": "ok", "version": __version__}


@router.get("/")
def index(user=Depends(current_user)):
    return RedirectResponse("/recommend" if user else "/login", status_code=303)


# --- вход / выход ---
@router.get("/login")
def login_form(request: Request, user=Depends(current_user)):
    if user:
        return RedirectResponse("/recommend", status_code=303)
    return _page(request, "login.html", None, {"demo_accounts": DEMO_ACCOUNTS})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...),
          csrf: str = Form(...), session: Session = Depends(get_session)):
    _verify_csrf(request, csrf)
    try:
        u = auth.authenticate(session, email=email, password=password)
    except (auth.AuthError, auth.AccountLocked) as e:
        return _page(request, "login.html", None,
                     {"error": str(e), "email": email, "demo_accounts": DEMO_ACCOUNTS})
    token = auth.create_session(session, u)
    resp = RedirectResponse("/recommend", status_code=303)
    set_session_cookie(resp, token)
    set_csrf_cookie(resp, csrf_token(request))
    return resp


@router.post("/logout")
def logout(request: Request, csrf: str = Form(...),
           session: Session = Depends(get_session)):
    _verify_csrf(request, csrf)
    tok = request.cookies.get(SESSION_COOKIE)
    if tok:
        auth.logout(session, tok)
    resp = RedirectResponse("/login", status_code=303)
    clear_session_cookie(resp)
    return resp


# --- регистрация / верификация почты ---
@router.get("/register")
def register_form(request: Request, user=Depends(current_user)):
    if user:
        return RedirectResponse("/recommend", status_code=303)
    return _page(request, "register.html", None, {})


@router.post("/register")
def register_submit(request: Request, email: str = Form(...), password: str = Form(...),
                    name: str = Form(""), consent: str = Form(""), marketing: str = Form(""),
                    csrf: str = Form(...), session: Session = Depends(get_session)):
    _verify_csrf(request, csrf)
    try:
        u = auth.register(session, email=email, password=password, name=(name or None),
                          consent=bool(consent), marketing=bool(marketing))
    except auth.ConsentRequired:
        return _page(request, "register.html", None,
                     {"error": "Нужно согласие на обработку персональных данных",
                      "email": email, "name": name})
    except auth.AuthError as e:
        return _page(request, "register.html", None,
                     {"error": str(e), "email": email, "name": name})
    # почтового транспорта пока нет (no-op outbox) — показываем ссылку верификации здесь (dev)
    token = auth.request_email_verification(session, u)
    return _page(request, "register_done.html", None,
                 {"email": email, "verify_url": f"/verify?token={token}"})


@router.get("/verify")
def verify(request: Request, token: str = "", session: Session = Depends(get_session)):
    try:
        auth.verify_email(session, token)
        return _page(request, "verify.html", None, {"ok": True})
    except auth.AuthError as e:
        return _page(request, "verify.html", None, {"ok": False, "msg": str(e)})


# --- сброс пароля ---
@router.get("/forgot")
def forgot_form(request: Request, user=Depends(current_user)):
    if user:
        return RedirectResponse("/recommend", status_code=303)
    return _page(request, "forgot.html", None, {})


@router.post("/forgot")
def forgot_submit(request: Request, email: str = Form(...), csrf: str = Form(...),
                  session: Session = Depends(get_session)):
    _verify_csrf(request, csrf)
    token = auth.request_password_reset(session, email)
    # не раскрываем, существует ли аккаунт; почты нет → для dev показываем ссылку, если выдан токен
    reset_url = f"/reset?token={token}" if token else None
    return _page(request, "forgot_done.html", None, {"email": email, "reset_url": reset_url})


@router.get("/reset")
def reset_form(request: Request, token: str = ""):
    return _page(request, "reset.html", None, {"token": token})


@router.post("/reset")
def reset_submit(request: Request, token: str = Form(...), password: str = Form(...),
                 csrf: str = Form(...), session: Session = Depends(get_session)):
    _verify_csrf(request, csrf)
    try:
        auth.reset_password(session, token, password)
    except auth.AuthError as e:
        return _page(request, "reset.html", None, {"token": token, "error": str(e)})
    return RedirectResponse("/login", status_code=303)


# --- анкета (холодный старт) ---
PACE_OPTIONS = [("relaxed", "Расслабленно"), ("balanced", "Баланс"), ("marathon", "Марафон")]
INTEREST_OPTIONS = [("new", "Открывать новое"), ("deep", "Глубже в любимое")]


@router.get("/questionnaire")
def questionnaire_form(request: Request, user=Depends(current_user),
                       session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    fest = get_active(session)
    authors, current = [], None
    if fest is not None:
        authors = session.exec(select(Author).where(
            Author.festival_id == fest.id).order_by(Author.name)).all()
        current = load_prefs(session, user.id, fest.id)
    fav_ids = set()
    if current is not None and fest is not None:
        from figaro.domain.models import UserPreferences
        p = session.get(UserPreferences, (user.id, fest.id))
        fav_ids = set(p.favorite_author_ids or []) if p else set()
    return _page(request, "questionnaire.html", user,
                 {"festival": fest, "authors": authors, "fav_ids": fav_ids,
                  "current": current, "pace_options": PACE_OPTIONS,
                  "interest_options": INTEREST_OPTIONS})


@router.post("/questionnaire")
def questionnaire_save(request: Request, csrf: str = Form(...),
                       pace: str = Form(""), interest_vector: str = Form(""),
                       author_ids: List[int] = Form(default=[]),
                       user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    save_preferences(session, user_id=user.id, festival_id=fest.id, pace=pace,
                     interest_vector=interest_vector, favorite_author_ids=author_ids)
    return RedirectResponse("/recommend", status_code=303)


# --- подбор маршрутов ---
@router.get("/recommend")
def recommend_page(request: Request, user=Depends(current_user),
                   session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    fest = get_active(session)
    groups = []
    has_prefs = False
    if fest is not None:
        has_prefs = load_prefs(session, user.id, fest.id) is not None
        prof = profile_for_user(session, user.id, fest.id)
        titles = {a.key: a.title for a in session.exec(
            select(Archetype).where(Archetype.festival_id == fest.id)).all()}
        res = recommend(session, fest.id, prof)
        for key, cards in res.items():
            # темп анкеты влияет на длину маршрута: фильтр по числу концертов (с релаксацией)
            cards = relax_by_concert_count(cards, 1, prof.target_max_concerts)[0]
            if cards:
                groups.append({"title": titles.get(key, key), "cards": cards})
    return _page(request, "recommend.html", user,
                 {"festival": fest, "groups": groups, "has_prefs": has_prefs})


# --- маршрутный лист ---
@router.get("/sheet")
def sheet_page(request: Request, sheet_id: Optional[int] = None,
               user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    fest = get_active(session)
    if sheet_id is not None:
        sheet = _owned_sheet(session, sheet_id, user)
    else:
        q = select(RouteSheet).where(RouteSheet.user_id == user.id)
        if fest is not None:
            q = q.where(RouteSheet.festival_id == fest.id)
        sheet = session.exec(q.order_by(RouteSheet.id.desc())).first()
        if sheet is None and fest is not None:
            sheet = sheets.create_empty(session, user.id, fest.id)
    if sheet is None:
        return _page(request, "recommend.html", user, {"festival": fest, "groups": []})
    return _page(request, "sheet.html", user,
                 {"festival": fest, "view": _sheet_view(session, sheet)})


@router.post("/sheet/new")
def sheet_new(request: Request, csrf: str = Form(...), user=Depends(current_user),
              session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    sheet = sheets.create_empty(session, user.id, fest.id)
    return RedirectResponse(f"/sheet?sheet_id={sheet.id}", status_code=303)


@router.post("/sheet/from-route/{day_route_id}")
def sheet_from_route(request: Request, day_route_id: int, csrf: str = Form(...),
                     user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    sheet = sheets.create_from_route(session, user.id, fest.id, day_route_id)
    return RedirectResponse(f"/sheet?sheet_id={sheet.id}", status_code=303)


@router.post("/sheet/{sheet_id}/add/{concert_id}")
def sheet_add(request: Request, sheet_id: int, concert_id: int, csrf: str = Form(...),
              user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        raise HTTPException(401)
    _verify_csrf(request, csrf)
    sheet = _owned_sheet(session, sheet_id, user)
    res = sheets.add_concert(session, sheet, concert_id)
    return _sheet_partial(request, session, user, sheet,
                          notice=None if res.added else res.reason)


@router.post("/sheet/{sheet_id}/remove/{concert_id}")
def sheet_remove(request: Request, sheet_id: int, concert_id: int, csrf: str = Form(...),
                 user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        raise HTTPException(401)
    _verify_csrf(request, csrf)
    sheet = _owned_sheet(session, sheet_id, user)
    sheets.remove_concert(session, sheet, concert_id)
    return _sheet_partial(request, session, user, sheet)


@router.post("/sheet/{sheet_id}/pin/{concert_id}")
def sheet_pin(request: Request, sheet_id: int, concert_id: int, csrf: str = Form(...),
              user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        raise HTTPException(401)
    _verify_csrf(request, csrf)
    sheet = _owned_sheet(session, sheet_id, user)
    cur = session.exec(select(RouteSheetItem).where(
        RouteSheetItem.route_sheet_id == sheet.id,
        RouteSheetItem.concert_id == concert_id)).first()
    sheets.set_pin(session, sheet, concert_id, pinned=not (cur.is_pinned if cur else False))
    return _sheet_partial(request, session, user, sheet)


# --- дашборды исследователя (RBAC: researcher/admin) ---
def _require_research(user) -> None:
    if not user or not auth.can_access(user.role, "дашборды"):
        raise auth.Forbidden("403")


@router.get("/research")
def research(request: Request, user=Depends(current_user),
             session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_research(user)
    fest = get_active(session)
    ctx = {"festival": fest, "overview": None, "supply": [], "timeline": [], "customers": None}
    if fest is not None:
        ctx["overview"] = analytics.festival_overview(session, fest.id)
        ctx["supply"] = analytics.archetype_supply(session, fest.id)
        ctx["timeline"] = analytics.availability_timeline(session, fest.id)
        ctx["customers"] = analytics.customer_purchase_counts(session, fest.id)
    return _page(request, "research.html", user, ctx)


# --- админский пульт эмуляции (RBAC: только admin) ---
def _require_admin(user) -> None:
    if not user or not auth.can_access(user.role, "пульт эмуляции"):
        raise auth.Forbidden("403")


def _save_clock(request: Request) -> None:
    path = request.app.state.clock_path
    if path:  # в тестах None → на диск не пишем
        request.app.state.clock.save(path)


def _parse_dt(raw: Optional[str]) -> datetime:
    if not raw:
        raise HTTPException(400, "нужна дата/время")
    return datetime.fromisoformat(raw)


def _pult_view(request: Request, user, session: Session):
    clock = request.app.state.clock
    fest = get_active(session)
    now = clock.now().replace(tzinfo=None)
    ctx = {"festival": fest, "clock_mode": clock.mode.value, "virtual_now": now,
           "phase": None, "sim_mode": None, "seed": None, "on_sale": 0, "sold_out": 0}
    if fest is not None:
        ctx["phase"] = phase_for(now.date(), fest.sales_start_on,
                                 fest.starts_on, fest.ends_on).value
        sim = availability.get_sim_state(session, fest.id)
        ctx["sim_mode"], ctx["seed"] = sim.availability_mode, sim.seed
        for c in session.exec(select(Concert).where(Concert.festival_id == fest.id)).all():
            if availability.is_on_sale(session, c.id):
                ctx["on_sale"] += 1
            else:
                ctx["sold_out"] += 1
    return _page(request, "pult.html", user, ctx)


@router.get("/admin/pult")
def pult(request: Request, user=Depends(current_user),
         session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_admin(user)
    return _pult_view(request, user, session)


@router.post("/admin/pult/clock")
def pult_clock(request: Request, csrf: str = Form(...), mode: str = Form("real"),
               virtual: str = Form(""), speed: float = Form(1.0),
               user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_admin(user)
    _verify_csrf(request, csrf)
    clock = request.app.state.clock
    if mode == "real":
        clock.set_real()
    elif mode == "offset":
        clock.set_offset(_parse_dt(virtual))
    elif mode == "accelerated":
        clock.set_accelerated(_parse_dt(virtual), speed)
    else:
        raise HTTPException(400, "неизвестный режим часов")
    _save_clock(request)
    return RedirectResponse("/admin/pult", status_code=303)


@router.post("/admin/pult/availability")
def pult_availability(request: Request, csrf: str = Form(...),
                      mode: str = Form("sim_curve"), seed: int = Form(42),
                      user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_admin(user)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    availability.set_mode(session, fest.id, mode, seed)
    availability.tick(session, fest.id, request.app.state.clock)  # пересчёт под виртуальное время
    return RedirectResponse("/admin/pult", status_code=303)


@router.post("/admin/pult/recompute")
def pult_recompute(request: Request, csrf: str = Form(...),
                   user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_admin(user)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    availability.tick(session, fest.id, request.app.state.clock)
    return RedirectResponse("/admin/pult", status_code=303)


@router.post("/admin/pult/reset")
def pult_reset(request: Request, csrf: str = Form(...),
               user=Depends(current_user), session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse("/login", status_code=303)
    _require_admin(user)
    _verify_csrf(request, csrf)
    fest = get_active(session)
    if fest is None:
        raise HTTPException(409, "нет активного фестиваля")
    availability.reset_to_sales_start(session, fest.id)
    return RedirectResponse("/admin/pult", status_code=303)
