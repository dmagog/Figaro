from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
from auth.authenticate import authenticate_cookie
import logging
from sqlmodel import select, func  # Используем из sqlmodel

settings = get_settings()
admin_halls_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_halls_router.get("/admin/halls", response_class=HTMLResponse)
async def admin_halls(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)

    from models import Hall, Concert, Purchase, HallTransition
    halls = session.exec(select(Hall)).all()
    concerts = session.exec(select(Concert)).all()
    transitions = session.exec(select(HallTransition)).all()

    # Группируем концерты по залу
    concerts_by_hall = {}
    for c in concerts:
        concerts_by_hall.setdefault(c.hall_id, []).append(c)

    from services.crud.tickets import get_tickets_left

    # Статистика по залам
    hall_stats = {h.id: {"concerts": 0, "seats": h.seats, "tickets_sold": 0, "available_concerts": 0} for h in halls}
    for c in concerts:
        hall_id = c.hall_id
        if hall_id in hall_stats:
            hall_stats[hall_id]["concerts"] += 1
            hall_stats[hall_id]["seats"] = hall_stats[hall_id]["seats"] or 0
            tickets_left = get_tickets_left(c.id)
            if tickets_left > 0:
                hall_stats[hall_id]["available_concerts"] += 1

    # Количество купленных билетов по каждому залу
    result = session.exec(
        select(Concert.hall_id, func.count(Purchase.id))
        .join(Purchase, Purchase.concert_id == Concert.id)
        .group_by(Concert.hall_id)
    ).all()
    tickets_per_hall = {row[0]: row[1] for row in result}
    for hall_id, tickets in tickets_per_hall.items():
        if hall_id in hall_stats:
            hall_stats[hall_id]["tickets_sold"] = tickets

    halls_data = []
    all_fill_percents = []
    for h in halls:
        stats = hall_stats[h.id]
        fill_percent = (stats["tickets_sold"] / (stats["seats"] * stats["concerts"]) * 100) if stats["seats"] and stats["concerts"] else 0
        fill_percents = []
        for c in concerts_by_hall.get(h.id, []):
            seats = h.seats or 0
            if seats > 0:
                tickets_row = session.exec(select(func.count(Purchase.id)).where(Purchase.concert_id == c.id)).first()
                tickets = tickets_row or 0
                fill_percents.append((tickets / seats) * 100)
                all_fill_percents.append((tickets / seats) * 100)
        mean_fill_percent = round(sum(fill_percents) / len(fill_percents), 1) if fill_percents else 0
        halls_data.append({
            "hall": h,
            "concerts": stats["concerts"],
            "seats": stats["seats"],
            "tickets_sold": stats["tickets_sold"],
            "fill_percent": fill_percent,
            "available_concerts": stats["available_concerts"],
            "mean_fill_percent": mean_fill_percent
        })
    mean_fill_percent_all_halls = round(sum(all_fill_percents) / len(all_fill_percents), 1) if all_fill_percents else 0
    hall_ids = [h["hall"].id for h in halls_data]

    halls_by_id = {h.id: h for h in halls}
    hall_names = [h.name for h in halls]

    transitions_matrix = {}
    for from_hall in halls:
        transitions_matrix[from_hall.name] = {}
        for to_hall in halls:
            transitions_matrix[from_hall.name][to_hall.name] = None
    for transition in transitions:
        from_hall = halls_by_id.get(transition.from_hall_id)
        to_hall = halls_by_id.get(transition.to_hall_id)
        if from_hall and to_hall:
            transitions_matrix[from_hall.name][to_hall.name] = transition.transition_time

    context = {
        "user": user_obj,
        "halls_data": halls_data,
        "hall_ids": hall_ids,
        "mean_fill_percent_all_halls": mean_fill_percent_all_halls,
        "transitions_matrix": transitions_matrix,
        "hall_names": hall_names,
        "request": request
    }
    return templates.TemplateResponse("admin_halls.html", context) 