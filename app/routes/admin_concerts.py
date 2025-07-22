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
admin_concerts_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_concerts_router.get("/admin/concerts", response_class=HTMLResponse)
async def admin_concerts(request: Request, session=Depends(get_session)):
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

    from models import Concert, Hall, Purchase
    concerts = session.exec(select(Concert)).all()
    halls = {h.id: h for h in session.exec(select(Hall)).all()}

    result = session.exec(
        select(Purchase.concert_id, func.count(Purchase.id)).group_by(Purchase.concert_id)
    ).all()
    tickets_per_concert = {row[0]: row[1] for row in result}

    concerts_data = []
    available_count = 0
    unavailable_count = 0
    for c in concerts:
        hall = halls.get(c.hall_id)
        seats = hall.seats if hall else 0
        tickets_left = c.tickets_left if c.tickets_left is not None else seats
        tickets_available = getattr(c, 'tickets_available', None)
        tickets_available = tickets_available and tickets_left > 0
        tickets_sold = tickets_per_concert.get(c.id, 0)
        fill_percent = (tickets_sold / seats * 100) if seats else 0
        if tickets_available:
            available_count += 1
        else:
            unavailable_count += 1
        concerts_data.append({
            'concert': c,
            'hall': hall,
            'seats': seats,
            'tickets_left': tickets_left,
            'tickets_available': tickets_available,
            'tickets_sold': tickets_sold,
            'fill_percent': fill_percent
        })

    concert_days = []
    seen = set()
    for item in concerts_data:
        dt = getattr(item['concert'], 'datetime', None)
        if dt:
            day = dt.date()
            if day not in seen:
                concert_days.append(day)
                seen.add(day)
    concert_days.sort()

    context = {
        "user": user_obj,
        "concerts_data": concerts_data,
        "concert_days": concert_days,
        "available_count": available_count,
        "unavailable_count": unavailable_count,
        "request": request
    }
    return templates.TemplateResponse("admin_concerts.html", context) 