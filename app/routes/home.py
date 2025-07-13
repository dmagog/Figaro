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
from sqlalchemy import select


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
            user_stats[u.id] = {"count": 0, "spent": 0}
            continue
        count = session.exec(select(func.count(Purchase.id)).where(Purchase.user_external_id == str(ext_id))).scalar_one()
        spent = session.exec(select(func.coalesce(func.sum(Purchase.price), 0)).where(Purchase.user_external_id == str(ext_id))).scalar_one()
        user_stats[u.id] = {"count": count, "spent": spent}

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
    for p, c, u, h in purchases:
        if u.email not in unique_users:
            unique_users[u.email] = u.name or u.email
        if c.id not in unique_concerts:
            unique_concerts[c.id] = c.name

    context = {
        "user": user_obj,
        "purchases": purchases,
        "unique_users": unique_users,
        "unique_concerts": unique_concerts,
        "request": request
    }
    return templates.TemplateResponse("admin_purchases.html", context)