"""HTTP-маршруты веб-слоя (server-rendered + HTMX). Логики нет — только проводка к services/*.

Первый срез: упрощённый вход, подбор маршрутов, редактирование маршрутного листа
(добавить/убрать/закрепить) с подсказками концертов и офф-программы.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from figaro.domain.models import (Archetype, Author, Concert, Hall, RouteSheet,
                                  RouteSheetItem)
from figaro.services import auth, sheets
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

DEMO_ACCOUNTS = ["user@figaro.dev / figaro12345"]


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
