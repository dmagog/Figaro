from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
from auth.hash_password import HashPassword
from database.config import get_settings
from database.database import get_session
from services.crud import user as UsersService
from services.crud.purchase import get_festival_summary_stats
import pandas as pd
from typing import Dict
from sqlalchemy import select, func


settings = get_settings()
home_route = APIRouter()
hash_password = HashPassword()
templates = Jinja2Templates(directory="templates")


@home_route.get("/", response_class=HTMLResponse)
async def index(request: Request, session=Depends(get_session)):
    """
    Главная страница приложения.
    
    Args:
        request (Request): Объект запроса FastAPI

    Returns:
        HTMLResponse: HTML страница с контекстом пользователя
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    context = {
        "login": user,
        "request": request
    }

    if user:
        user_exist = UsersService.get_user_by_email(context['login'], session)
        if user_exist is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
        
        context['user'] = user_exist


    return templates.TemplateResponse("index.html", context)


@home_route.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request, session=Depends(get_session)):
    """
    Главная страница админки. Доступ только для суперадмина.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    # Получаем полноценного пользователя из БД
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    summary = get_festival_summary_stats(session)

    context = {
        "user": user_obj,
        "request": request,
        "summary": summary
    }
    return templates.TemplateResponse("admin_index.html", context)


@home_route.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    # Получаем всех пользователей
    users = session.exec(select(UsersService.User)).scalars().all()

    # Для каждого пользователя считаем покупки и сумму трат
    from models import Purchase
    from sqlalchemy import func
    user_stats = {}
    for u in users:
        print('USER:', u, getattr(u, '__dict__', None))  # DEBUG
        ext_id = getattr(u, 'external_id', None)
        if not ext_id:
            user_stats[u.id] = {"count": 0, "spent": 0, "unique_concerts": 0, "tickets": 0}
            continue
        # Все покупки пользователя
        purchases = session.exec(select(Purchase).where(Purchase.user_external_id == str(ext_id))).scalars().all()
        unique_concerts = len(set(p.concert_id for p in purchases))
        tickets = len(purchases)
        spent = sum(p.price or 0 for p in purchases)
        user_stats[u.id] = {"count": tickets, "spent": spent, "unique_concerts": unique_concerts, "tickets": tickets}

    users_with_purchases_count = sum(1 for u in users if user_stats.get(u.id, {}).get('count', 0) > 0)

    context = {
        "user": user_obj,
        "users": users,
        "user_stats": user_stats,
        "users_with_purchases_count": users_with_purchases_count,
        "request": request
    }
    return templates.TemplateResponse("admin_users.html", context)


@home_route.get("/admin/purchases", response_class=HTMLResponse)
async def admin_purchases(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None

    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    from models import Purchase, Concert, User, Hall
    from sqlalchemy import select
    # Получаем все покупки с деталями
    purchases = session.exec(
        select(Purchase, Concert, User, Hall)
        .join(Concert, Purchase.concert_id == Concert.id)
        .join(User, Purchase.user_external_id == User.external_id)
        .join(Hall, Concert.hall_id == Hall.id)
        .order_by(Purchase.purchased_at.desc())
    ).all()

    # Уникальные пользователи и концерты для фильтров
    unique_users = {}
    unique_concerts = {}
    # Для фильтров по дате: ищем min/max дату покупки
    from datetime import datetime
    purchase_dates = [p.purchased_at for p, _, _, _ in purchases if p.purchased_at]
    if purchase_dates:
        min_purchase_date = min(purchase_dates).strftime('%Y-%m-%d')
        max_purchase_date = max(purchase_dates).strftime('%Y-%m-%d')
    else:
        min_purchase_date = ''
        max_purchase_date = ''
    for p, c, u, h in purchases:
        if u.email not in unique_users:
            unique_users[u.email] = u.name or u.email
        if c.id not in unique_concerts:
            unique_concerts[c.id] = c.name

    # Группировка покупок по (user_external_id, concert_id, purchased_at)
    from collections import defaultdict
    purchases_grouped = []
    grouped = defaultdict(list)
    for p, c, u, h in purchases:
        key = (u.external_id, c.id, p.purchased_at)
        grouped[key].append((p, c, u, h))
    for group in grouped.values():
        count = len(group)
        p, c, u, h = group[0]
        purchases_grouped.append({
            'purchase': p,
            'concert': c,
            'user': u,
            'hall': h,
            'tickets_count': count,
            'price': p.price,
        })
    context = {
        "user": user_obj,
        "purchases": purchases_grouped,
        "unique_users": unique_users,
        "unique_concerts": unique_concerts,
        "min_purchase_date": min_purchase_date,
        "max_purchase_date": max_purchase_date,
        "request": request
    }
    return templates.TemplateResponse("admin_purchases.html", context)


@home_route.get("/admin/concerts", response_class=HTMLResponse)
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    from models import Concert, Hall
    from models import Purchase
    from sqlalchemy import select, func
    concerts = session.exec(select(Concert)).scalars().all()
    halls = {h.id: h for h in session.exec(select(Hall)).scalars().all()}

    # Заглушка для количества оставшихся билетов
    def get_tickets_left(concert_id):
        import random
        return random.randint(0, 20)

    # Получаем количество купленных билетов по каждому концерту
    tickets_per_concert = dict(
        session.exec(
            select(Purchase.concert_id, func.count(Purchase.id)).group_by(Purchase.concert_id)
        ).all()
    )

    concerts_data = []
    available_count = 0
    unavailable_count = 0
    for c in concerts:
        hall = halls.get(c.hall_id)
        seats = hall.seats if hall else 0
        tickets_left = get_tickets_left(c.id)
        tickets_available = tickets_left > 0
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

    # Формируем список уникальных дней концертов
    concert_days = []
    seen = set()
    for item in concerts_data:
        dt = item['concert'].datetime
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


@home_route.get("/admin/halls", response_class=HTMLResponse)
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")

    from models import Hall, Concert, Purchase
    from sqlalchemy import select, func
    halls = session.exec(select(Hall)).scalars().all()
    concerts = session.exec(select(Concert)).scalars().all()

    # Заглушка для количества оставшихся билетов (как на концертах)
    def get_tickets_left(concert_id):
        import random
        return random.randint(0, 20)

    # Считаем количество концертов и мест по каждому залу
    hall_stats = {h.id: {"concerts": 0, "seats": h.seats, "tickets_sold": 0, "available_concerts": 0} for h in halls}
    for c in concerts:
        if c.hall_id in hall_stats:
            hall_stats[c.hall_id]["concerts"] += 1
            hall_stats[c.hall_id]["seats"] = hall_stats[c.hall_id]["seats"] or 0
            tickets_left = get_tickets_left(c.id)
            if tickets_left > 0:
                hall_stats[c.hall_id]["available_concerts"] += 1

    # Считаем количество купленных билетов по каждому залу
    tickets_per_hall = dict(
        session.exec(
            select(Concert.hall_id, func.count(Purchase.id))
            .join(Purchase, Purchase.concert_id == Concert.id)
            .group_by(Concert.hall_id)
        ).all()
    )
    for hall_id, tickets in tickets_per_hall.items():
        if hall_id in hall_stats:
            hall_stats[hall_id]["tickets_sold"] = tickets

    # Формируем данные для шаблона
    halls_data = []
    for h in halls:
        stats = hall_stats[h.id]
        fill_percent = (stats["tickets_sold"] / (stats["seats"] * stats["concerts"]) * 100) if stats["seats"] and stats["concerts"] else 0
        halls_data.append({
            "hall": h,
            "concerts": stats["concerts"],
            "seats": stats["seats"],
            "tickets_sold": stats["tickets_sold"],
            "fill_percent": fill_percent,
            "available_concerts": stats["available_concerts"]
        })

    context = {
        "user": user_obj,
        "halls_data": halls_data,
        "request": request
    }
    return templates.TemplateResponse("admin_halls.html", context)