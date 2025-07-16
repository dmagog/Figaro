from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import logging
from auth.authenticate import authenticate_cookie, authenticate
from auth.hash_password import HashPassword
from database.config import get_settings
from database.database import get_session
from services.crud import user as UsersService
from services.crud.purchase import get_festival_summary_stats
import pandas as pd
from typing import Dict
from sqlalchemy import select, func
from services.crud.data_loader import load_routes_from_csv
from config_data_path import ROUTES_PATH
import shutil
import os
import threading
import logging


def format_time_minutes(minutes):
    """
    Форматирует время в минутах в понятный для пользователя формат.
    
    Args:
        minutes (float): Время в минутах
        
    Returns:
        str: Отформатированное время в формате "Xч Yм" или "Yм"
    """
    if minutes is None:
        return "Н/Д"
    
    total_minutes = int(minutes)
    hours = total_minutes // 60
    remaining_minutes = total_minutes % 60
    
    if hours > 0 and remaining_minutes > 0:
        return f"{hours}ч {remaining_minutes}м"
    elif hours > 0:
        return f"{hours}ч"
    else:
        return f"{remaining_minutes}м"


settings = get_settings()
home_route = APIRouter()
hash_password = HashPassword()
templates = Jinja2Templates(directory="templates")

# Глобальный статус загрузки маршрутов
route_upload_status = {"in_progress": False, "progress": 0, "total": 0, "added": 0, "updated": 0, "error": None}

# Глобальный статус проверки AvailableRoute
available_routes_status = {"in_progress": False, "progress": 0, "total": 0, "available_count": 0, "total_routes": 0, "availability_percentage": 0, "error": None}

def process_routes_upload(session, path):
    global route_upload_status, available_routes_status
    try:
        route_upload_status["in_progress"] = True
        route_upload_status["progress"] = 0
        route_upload_status["added"] = 0
        route_upload_status["updated"] = 0
        route_upload_status["error"] = None
        # Загружаем маршруты с передачей status_dict
        from services.crud.data_loader import load_routes_from_csv
        result = load_routes_from_csv(session, path, status_dict=route_upload_status)
        route_upload_status["added"] = result["added"]
        route_upload_status["updated"] = result["updated"]
        
        # После загрузки маршрутов запускаем проверку AvailableRoute
        process_available_routes_check(session)
        
    except Exception as e:
        route_upload_status["error"] = str(e)
    finally:
        route_upload_status["in_progress"] = False


def process_available_routes_check(session):
    global available_routes_status
    try:
        available_routes_status["in_progress"] = True
        available_routes_status["progress"] = 0
        available_routes_status["available_count"] = 0
        available_routes_status["total_routes"] = 0
        available_routes_status["availability_percentage"] = 0
        available_routes_status["error"] = None
        
        # Импортируем необходимые модули
        from services.crud import route_service
        from models import Route, AvailableRoute
        from sqlmodel import select
        
        # Получаем общее количество маршрутов
        total_routes = len(session.exec(select(Route)).all())
        available_routes_status["total_routes"] = total_routes
        available_routes_status["total"] = total_routes
        
        # Проверяем, есть ли уже AvailableRoute
        existing_count = len(session.exec(select(AvailableRoute)).all())
        
        if existing_count == 0:
            # Если AvailableRoute нет, инициализируем их
            logging.info("AvailableRoute не найдены, начинаем инициализацию...")
            result = route_service.init_available_routes(session, status_dict=available_routes_status)
            available_routes_status["available_count"] = result["available_routes"]
            available_routes_status["availability_percentage"] = result["availability_percentage"] if "availability_percentage" in result else 0
        else:
            # Если AvailableRoute есть, обновляем их
            logging.info(f"Найдено {existing_count} AvailableRoute, обновляем...")
            result = route_service.update_available_routes(session, status_dict=available_routes_status)
            available_routes_status["available_count"] = result["current_count"]
            available_routes_status["availability_percentage"] = round((result["current_count"] / total_routes * 100), 2) if total_routes > 0 else 0
        
        available_routes_status["progress"] = total_routes
        
    except Exception as e:
        available_routes_status["error"] = str(e)
        logging.error(f"Ошибка при проверке AvailableRoute: {e}")
    finally:
        available_routes_status["in_progress"] = False


def get_user_field(u, field):
    # Если кортеж (например, (User,)), берём первый элемент
    if isinstance(u, tuple):
        u = u[0]
    return getattr(u, field, None)


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
        return RedirectResponse(url="/login", status_code=302)

    summary = get_festival_summary_stats(session)
    # Получаем количество маршрутов из кэша
    routes_count = summary.get("routes_count", 0)

    context = {
        "user": user_obj,
        "request": request,
        "summary": summary,
        "routes_count": routes_count
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
        return RedirectResponse(url="/login", status_code=302)

    # Получаем всех пользователей
    users = session.exec(select(UsersService.User)).scalars().all()
    # Для каждого пользователя считаем покупки и сумму трат
    from models import Purchase
    from sqlalchemy import func
    user_stats = {}
    for u in users:
        print('USER:', u, getattr(u, '__dict__', None))  # DEBUG
        ext_id = get_user_field(u, 'external_id')
        user_id = get_user_field(u, 'id')
        if not user_id:
            continue  # пропускаем пользователей без id
        if not ext_id:
            user_stats[user_id] = {"count": 0, "spent": 0, "unique_concerts": 0, "tickets": 0}
            continue
        # Все покупки пользователя
        purchases = session.exec(select(Purchase).where(Purchase.user_external_id == str(ext_id))).scalars().all()
        unique_concerts = len(set(p.concert_id for p in purchases))
        tickets = len(purchases)
        spent = sum(p.price or 0 for p in purchases)
        user_stats[user_id] = {"count": tickets, "spent": spent, "unique_concerts": unique_concerts, "tickets": tickets}

    users_with_purchases_count = sum(1 for u in users if get_user_field(u, 'id') and user_stats.get(get_user_field(u, 'id'), {}).get('count', 0) > 0)

    # Загружаем информацию о маршрутах пользователей
    route_matches = {}
    try:
        from models import CustomerRouteMatch, Route
        # Получаем все маршруты для быстрого доступа
        routes = session.exec(select(Route)).all()
        routes_by_id = {}
        for route in routes:
            if hasattr(route, 'id') and route.id is not None:
                routes_by_id[route.id] = route
        
        matches = session.exec(select(CustomerRouteMatch)).all()
        logging.info(f"Найдено {len(matches)} записей в CustomerRouteMatch")
        
        found_matches = 0
        for match in matches:
            # Получаем данные из Row объекта
            match_obj = match._mapping['CustomerRouteMatch']
            
            best_route = None
            if match_obj.found and match_obj.best_route_id:
                try:
                    best_route = routes_by_id.get(match_obj.best_route_id)
                    if best_route:
                        found_matches += 1
                except Exception as e:
                    logging.warning(f"Ошибка при получении маршрута {match_obj.best_route_id}: {e}")
                    best_route = None
            
            # Используем user_external_id как ключ для поиска
            route_matches[str(match_obj.user_external_id)] = {
                "found": match_obj.found,
                "match_type": match_obj.match_type,
                "reason": match_obj.reason,
                "customer_concerts": match_obj.customer_concerts.split(',') if match_obj.customer_concerts else [],
                "customer_concerts_str": match_obj.customer_concerts,
                "matched_routes": [],
                "best_match": {
                    "route_id": match_obj.best_route_id,
                    "route_composition": best_route.Sostav if best_route else None,
                    "route_days": best_route.Days if best_route else None,
                    "route_concerts": best_route.Concerts if best_route else None,
                    "route_halls": best_route.Halls if best_route else None,
                    "route_genre": best_route.Genre if best_route else None,
                    "route_show_time": best_route.ShowTime if best_route else None,
                    "route_trans_time": best_route.TransTime if best_route else None,
                    "route_wait_time": best_route.WaitTime if best_route else None,
                    "route_costs": best_route.Costs if best_route else None,
                    "route_comfort_score": best_route.ComfortScore if best_route else None,
                    "route_comfort_level": best_route.ComfortLevel if best_route else None,
                    "route_intellect_score": best_route.IntellectScore if best_route else None,
                    "route_intellect_category": best_route.IntellectCategory if best_route else None,
                    "match_type": match_obj.match_type,
                    "match_percentage": match_obj.match_percentage
                } if match_obj.found else None,
                "total_routes_checked": match_obj.total_routes_checked
            }
        
        logging.info(f"Из них найдено совпадений: {found_matches}")
        
    except Exception as e:
        logging.warning(f"Ошибка при получении маршрутов из базы: {e}")
        import traceback
        logging.warning(f"Полный traceback: {traceback.format_exc()}")
        route_matches = {}

    context = {
        "user": user_obj,
        "users": users,
        "user_stats": user_stats,
        "users_with_purchases_count": users_with_purchases_count,
        "route_matches": route_matches,
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
        return RedirectResponse(url="/login", status_code=302)

    from models import Purchase, Concert, User, Hall
    from sqlalchemy.orm import aliased
    from sqlalchemy import select, outerjoin
    # LEFT OUTER JOIN между Purchase и User
    UserAlias = aliased(User)
    stmt = (
        select(Purchase, Concert, UserAlias, Hall)
        .join(Concert, Purchase.concert_id == Concert.id)
        .join(Hall, Concert.hall_id == Hall.id)
        .outerjoin(UserAlias, Purchase.user_external_id == UserAlias.external_id)
        .order_by(Purchase.purchased_at.desc())
    )
    purchases = session.exec(stmt).all()

    # Уникальные пользователи и концерты для фильтров
    unique_users = {}
    unique_concerts = {}
    from datetime import datetime
    purchase_dates = [p.purchased_at for p, _, _, _ in purchases if p.purchased_at]
    if purchase_dates:
        min_purchase_date = min(purchase_dates).strftime('%Y-%m-%d')
        max_purchase_date = max(purchase_dates).strftime('%Y-%m-%d')
    else:
        min_purchase_date = ''
        max_purchase_date = ''
    # Только зарегистрированные пользователи (User), у которых есть покупки
    from models import User, Purchase
    users = session.exec(select(User)).scalars().all()
    users_with_purchases = set(
        row[0] for row in session.exec(select(Purchase.user_external_id).distinct()).all()
    )
    for u in users:
        if u.external_id and u.external_id in users_with_purchases and u.email and u.email not in unique_users:
            unique_users[u.email] = u.name or u.email
    for p, c, u, h in purchases:
        if c.id not in unique_concerts:
            unique_concerts[c.id] = c.name

    # Группировка покупок по (user_external_id, concert_id, purchased_at)
    from collections import defaultdict
    purchases_grouped = []
    grouped = defaultdict(list)
    for p, c, u, h in purchases:
        key = (p.user_external_id, c.id, p.purchased_at)
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
        return RedirectResponse(url="/login", status_code=302)

    from models import Concert, Hall
    from models import Purchase
    from sqlalchemy import select, func
    concerts = session.exec(select(Concert)).scalars().all()
    concerts_by_id = {getattr(c, 'id', None): c for c in concerts if hasattr(c, 'id') and getattr(c, 'id', None) is not None}
    halls = {h.id: h for h in session.exec(select(Hall)).scalars().all()}

    # Получаем количество купленных билетов по каждому концерту
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
        # Используем данные напрямую из базы данных
        tickets_left = c.tickets_left if c.tickets_left is not None else seats
        tickets_available = c.tickets_available and tickets_left > 0
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
        return RedirectResponse(url="/login", status_code=302)

    from models import Hall, Concert, Purchase
    from sqlalchemy import select, func
    halls = session.exec(select(Hall)).scalars().all()
    concerts = session.exec(select(Concert)).scalars().all()

    # Для расчёта средней заполняемости по каждому залу
    concerts_by_hall = {}
    for c in concerts:
        concerts_by_hall.setdefault(c.hall_id, []).append(c)

    # Используем новый сервис билетов
    from services.crud.tickets import get_tickets_left

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
    result = session.exec(
        select(Concert.hall_id, func.count(Purchase.id))
        .join(Purchase, Purchase.concert_id == Concert.id)
        .group_by(Concert.hall_id)
    ).all()
    tickets_per_hall = {row[0]: row[1] for row in result}
    for hall_id, tickets in tickets_per_hall.items():
        if hall_id in hall_stats:
            hall_stats[hall_id]["tickets_sold"] = tickets

    # Формируем данные для шаблона
    halls_data = []
    all_fill_percents = []
    for h in halls:
        stats = hall_stats[h.id]
        fill_percent = (stats["tickets_sold"] / (stats["seats"] * stats["concerts"]) * 100) if stats["seats"] and stats["concerts"] else 0
        # Средняя заполняемость по всем концертам этого зала
        fill_percents = []
        for c in concerts_by_hall.get(h.id, []):
            seats = h.seats or 0
            if seats > 0:
                # Считаем количество купленных билетов для этого концерта
                from models import Purchase
                tickets_row = session.exec(select(func.count(Purchase.id)).where(Purchase.concert_id == c.id)).scalars().first()
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
    context = {
        "user": user_obj,
        "halls_data": halls_data,
        "hall_ids": hall_ids,
        "mean_fill_percent_all_halls": mean_fill_percent_all_halls,
        "request": request
    }
    return templates.TemplateResponse("admin_halls.html", context)


@home_route.post("/admin/halls/update_seats")
async def update_hall_seats(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = None
    if token:
        user = await authenticate_cookie(token)
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    data = await request.json()
    hall_id = data.get('hall_id')
    new_seats = data.get('seats')
    if not hall_id or not isinstance(new_seats, int) or new_seats < 1:
        return JSONResponse({"success": False, "error": "Некорректные данные"}, status_code=400)
    from models import Hall
    from sqlalchemy import select
    hall = session.exec(select(Hall).where(Hall.id == hall_id)).scalars().first()
    if not hall:
        return JSONResponse({"success": False, "error": "Зал не найден"}, status_code=404)
    hall.seats = new_seats
    session.add(hall)
    session.commit()
    session.refresh(hall)
    return JSONResponse({"success": True, "seats": hall.seats})


@home_route.get("/admin/customers", response_class=HTMLResponse)
async def admin_customers(request: Request, session=Depends(get_session), load_routes: bool = Query(True, description="Загружать ли маршруты")):
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

    from models import Purchase, User, Concert, CustomerRouteMatch
    from sqlalchemy import select, func
    
    # Получаем все уникальные user_external_id из Purchase
    external_ids = set(str(row[0]) for row in session.exec(select(Purchase.user_external_id).distinct()).all())
    # Получаем всех пользователей с этими external_id (и вообще всех User)
    users_by_external = {str(u.external_id): u for u in session.exec(select(User)).scalars().all() if u.external_id is not None}
    # Получаем все концерты для быстрого доступа по id
    concerts = session.exec(select(Concert)).scalars().all()
    concerts_by_id = {c.id: c for c in concerts}
    
    # Получаем все соответствия маршрутов из таблицы CustomerRouteMatch
    route_matches = {}
    if load_routes:
        try:
            from models import Route
            # Получаем все маршруты для быстрого доступа
            routes = session.exec(select(Route)).all()
            routes_by_id = {}
            for route in routes:
                if hasattr(route, 'id') and route.id is not None:
                    routes_by_id[route.id] = route
            
            matches = session.exec(select(CustomerRouteMatch)).all()
            logging.info(f"Найдено {len(matches)} записей в CustomerRouteMatch")
            

            
            found_matches = 0
            for match in matches:
                # Получаем данные из Row объекта
                match_obj = match._mapping['CustomerRouteMatch']
                
                best_route = None
                if match_obj.found and match_obj.best_route_id:
                    try:
                        best_route = routes_by_id.get(match_obj.best_route_id)
                        if best_route:
                            found_matches += 1
                    except Exception as e:
                        logging.warning(f"Ошибка при получении маршрута {match_obj.best_route_id}: {e}")
                        best_route = None
                
                # Используем user_external_id как ключ для поиска
                route_matches[str(match_obj.user_external_id)] = {
                    "found": match_obj.found,
                    "match_type": match_obj.match_type,
                    "reason": match_obj.reason,
                    "customer_concerts": match_obj.customer_concerts.split(',') if match_obj.customer_concerts else [],
                    "customer_concerts_str": match_obj.customer_concerts,
                    "matched_routes": [],
                    "best_match": {
                        "route_id": match_obj.best_route_id,
                        "route_composition": best_route.Sostav if best_route else None,
                        "route_days": best_route.Days if best_route else None,
                        "route_concerts": best_route.Concerts if best_route else None,
                        "route_halls": best_route.Halls if best_route else None,
                        "route_genre": best_route.Genre if best_route else None,
                        "route_show_time": best_route.ShowTime if best_route else None,
                        "route_trans_time": best_route.TransTime if best_route else None,
                        "route_wait_time": best_route.WaitTime if best_route else None,
                        "route_costs": best_route.Costs if best_route else None,
                        "route_comfort_score": best_route.ComfortScore if best_route else None,
                        "route_comfort_level": best_route.ComfortLevel if best_route else None,
                        "route_intellect_score": best_route.IntellectScore if best_route else None,
                        "route_intellect_category": best_route.IntellectCategory if best_route else None,
                        "match_type": match_obj.match_type,
                        "match_percentage": match_obj.match_percentage
                    } if match_obj.found else None,
                    "total_routes_checked": match_obj.total_routes_checked
                }
            
            logging.info(f"Из них найдено совпадений: {found_matches}")
            
        except Exception as e:
            logging.warning(f"Ошибка при получении маршрутов из базы: {e}")
            import traceback
            logging.warning(f"Полный traceback: {traceback.format_exc()}")
            route_matches = {}
    
    customers = []
    customers_with_matches = 0
    for ext_id in external_ids:
        purchases = session.exec(select(Purchase).where(Purchase.user_external_id == ext_id)).scalars().all()
        total_spent = sum((p.price or 0) for p in purchases)
        unique_concerts = set(p.concert_id for p in purchases)
        unique_days = set(
            concerts_by_id[p.concert_id].datetime.date()
            for p in purchases
            if p.concert_id in concerts_by_id and concerts_by_id[p.concert_id].datetime
        )
        user = users_by_external.get(ext_id)
        
        # Получаем соответствие с маршрутами из кэша
        route_match = route_matches.get(ext_id, {
            "found": False,
            "reason": "Ошибка при получении данных",
            "customer_concerts": [],
            "matched_routes": []
        })
        
        if route_match["found"]:
            customers_with_matches += 1
        
        customers.append({
            "external_id": ext_id,
            "user": user,
            "total_purchases": len(purchases),
            "total_spent": total_spent,
            "unique_concerts": len(unique_concerts),
            "unique_days": len(unique_days),
            "route_match": route_match
        })
    
    # Передаём customers в шаблон
    return templates.TemplateResponse("admin_customers.html", {"request": request, "customers": customers})



@home_route.get("/api/customers/{external_id}/route-details")
async def get_customer_route_details(external_id: str, request: Request, session=Depends(get_session)):
    """
    API endpoint для получения детальной информации о маршруте покупателя
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    user = None
    if token:
        user = await authenticate_cookie(token)
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    
    try:
        from models import CustomerRouteMatch, Route
        match = session.exec(select(CustomerRouteMatch).where(CustomerRouteMatch.user_external_id == external_id)).first()
        
        if match:
            # Получаем данные из Row объекта
            match_obj = match._mapping['CustomerRouteMatch']
            
            best_route = None
            if match_obj.found and match_obj.best_route_id:
                try:
                    # Получаем полную информацию о маршруте
                    best_route = session.exec(select(Route).where(Route.id == match_obj.best_route_id)).first()
                    if not best_route:
                        logging.warning(f"Маршрут {match_obj.best_route_id} не найден в базе данных")
                except Exception as e:
                    logging.warning(f"Ошибка при получении маршрута {match_obj.best_route_id}: {e}")
                    best_route = None
            
            route_match = {
                "found": match_obj.found,
                "match_type": match_obj.match_type,
                "reason": match_obj.reason,
                "customer_concerts": match_obj.customer_concerts.split(',') if match_obj.customer_concerts else [],
                "customer_concerts_str": match_obj.customer_concerts,
                "matched_routes": [],
                "best_match": {
                    "route_id": match_obj.best_route_id,
                    "route_composition": best_route._mapping['Route'].Sostav if best_route else None,
                    "route_days": best_route._mapping['Route'].Days if best_route else None,
                    "route_concerts": best_route._mapping['Route'].Concerts if best_route else None,
                    "route_halls": best_route._mapping['Route'].Halls if best_route else None,
                    "route_genre": best_route._mapping['Route'].Genre if best_route else None,
                    "route_show_time": best_route._mapping['Route'].ShowTime if best_route else None,
                    "route_trans_time": best_route._mapping['Route'].TransTime if best_route else None,
                    "route_wait_time": best_route._mapping['Route'].WaitTime if best_route else None,
                    "route_costs": best_route._mapping['Route'].Costs if best_route else None,
                    "route_comfort_score": best_route._mapping['Route'].ComfortScore if best_route else None,
                    "route_comfort_level": best_route._mapping['Route'].ComfortLevel if best_route else None,
                    "route_intellect_score": best_route._mapping['Route'].IntellectScore if best_route else None,
                    "route_intellect_category": best_route._mapping['Route'].IntellectCategory if best_route else None,
                    "match_type": match_obj.match_type,
                    "match_percentage": match_obj.match_percentage
                } if match_obj.found else None,
                "total_routes_checked": match_obj.total_routes_checked
            }
        else:
            route_match = {
                "found": False,
                "reason": "Покупатель не найден",
                "customer_concerts": [],
                "matched_routes": []
            }
        
        return JSONResponse({
            "success": True,
            "route_match": route_match
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Ошибка при получении данных о маршруте: {str(e)}"
        }, status_code=500)


@home_route.post("/admin/users/update_external_id")
async def update_user_external_id(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = None
    if token:
        user = await authenticate_cookie(token)
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    data = await request.json()
    old_external_id = data.get('old_external_id')
    new_external_id = data.get('new_external_id')
    if not old_external_id or not new_external_id:
        return JSONResponse({"success": False, "error": "Некорректные данные"}, status_code=400)
    from models import User
    from sqlalchemy import select
    user = session.exec(select(User).where(User.external_id == old_external_id)).scalars().first()
    if not user:
        return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=404)
    # Проверка на уникальность нового external_id
    exists = session.exec(select(User).where(User.external_id == new_external_id)).scalars().first()
    if exists:
        return JSONResponse({"success": False, "error": "Такой external_id уже существует"}, status_code=409)
    user.external_id = new_external_id
    session.add(user)
    session.commit()
    return JSONResponse({"success": True})


@home_route.post("/admin/customers/update_external_id")
async def update_customer_external_id(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = None
    if token:
        user = await authenticate_cookie(token)
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    data = await request.json()
    old_external_id = data.get('old_external_id')
    new_external_id = data.get('new_external_id')
    if not old_external_id or not new_external_id:
        return JSONResponse({"success": False, "error": "Некорректные данные"}, status_code=400)
    from models import User
    from sqlalchemy import select
    user = session.exec(select(User).where(User.external_id == old_external_id)).scalars().first()
    if not user:
        return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=404)
    # Проверка на уникальность нового external_id
    exists = session.exec(select(User).where(User.external_id == new_external_id)).scalars().first()
    if exists:
        return JSONResponse({"success": False, "error": "Такой external_id уже существует"}, status_code=409)
    user.external_id = new_external_id
    session.add(user)
    session.commit()
    return JSONResponse({"success": True})


@home_route.get("/admin/routes", response_class=HTMLResponse)
async def admin_routes_redirect():
    return RedirectResponse(url="/admin/routes/upload", status_code=302)

@home_route.get("/admin/routes/upload", response_class=HTMLResponse)
async def admin_routes_upload(request: Request, session=Depends(get_session)):
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
    
    summary = get_festival_summary_stats(session)
    
    # Получаем данные о доступных маршрутах из Statistics
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    from models import Statistics
    from sqlmodel import select
    
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    
    # Получаем дату последней проверки доступных маршрутов
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    
    last_check_date = None
    if available_routes_stats and available_routes_stats.updated_at:
        last_check_date = available_routes_stats.updated_at
    
    context = {
        "user": user_obj,
        "request": request,
        "summary": summary,
        "active_tab": "upload",
        "available_routes_count": available_routes_count,
        "available_concerts_count": available_concerts_count,
        "last_check_date": last_check_date
    }
    return templates.TemplateResponse("admin_routes_upload.html", context)

@home_route.get("/admin/routes/concerts", response_class=HTMLResponse)
async def admin_routes_concerts(request: Request, session=Depends(get_session)):
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
    
    # Получаем количество маршрутов из кэша
    from services.crud.purchase import get_cached_routes_count
    routes_count = get_cached_routes_count(session)
    
    # Получаем данные о доступных маршрутах из Statistics
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    from models import Statistics, Concert
    from sqlmodel import select
    
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    
    # Получаем дату последней проверки доступных маршрутов
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    
    last_check_date = None
    if available_routes_stats and available_routes_stats.updated_at:
        last_check_date = available_routes_stats.updated_at
    
    # Получаем данные о всех концертах для отображения статуса
    concerts = session.exec(select(Concert).order_by(Concert.id.asc())).all()
    concerts_data = []
    
    # Группируем концерты по дням
    concerts_by_day = {}
    
    for concert in concerts:
        # Получаем информацию о зале
        hall = concert.hall
        seats = hall.seats if hall else 100
        tickets_left = concert.tickets_left if concert.tickets_left is not None else seats
        
        # Вычисляем процент доступности
        percent_left = (tickets_left / seats * 100) if seats > 0 else 0
        
        # Определяем цвет статуса
        if percent_left <= 10:
            status_color = '#e53935'  # красный
        elif percent_left <= 20:
            status_color = '#ffb300'  # жёлтый
        else:
            status_color = '#43a047'  # зелёный
        
        concert_data = {
            'id': concert.id,
            'name': concert.name,
            'tickets_available': concert.tickets_available,
            'tickets_left': tickets_left,
            'seats': seats,
            'percent_left': percent_left,
            'status_color': status_color,
            'datetime': concert.datetime
        }
        
        # Группируем по дню
        if concert.datetime:
            day_key = concert.datetime.date()
            if day_key not in concerts_by_day:
                concerts_by_day[day_key] = []
            concerts_by_day[day_key].append(concert_data)
        else:
            # Если нет даты, добавляем в общий список
            concerts_data.append(concert_data)
    
    # Создаем структуру данных, сгруппированную по дням
    concerts_by_day_sorted = {}
    sorted_days = sorted(concerts_by_day.keys())
    for day in sorted_days:
        # Сортируем концерты в дне по времени
        day_concerts = sorted(concerts_by_day[day], key=lambda x: x['datetime'])
        concerts_by_day_sorted[day] = day_concerts
    
    # Оставляем старый формат для обратной совместимости
    for day in sorted_days:
        concerts_data.extend(concerts_by_day_sorted[day])
    
    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "concerts",
        "routes_count": routes_count,
        "available_routes_count": available_routes_count,
        "available_concerts_count": available_concerts_count,
        "last_check_date": last_check_date,
        "concerts_data": concerts_data,
        "concerts_by_day": concerts_by_day_sorted
    }
    return templates.TemplateResponse("admin_routes_main.html", context)

@home_route.get("/admin/routes/view", response_class=HTMLResponse)
async def admin_routes_view(request: Request, session=Depends(get_session)):
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
    
    # Получаем параметры пагинации и сортировки
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 15))
    sort_by = request.query_params.get("sort_by", "concerts")  # Изменили дефолт на "concerts"
    sort_order = request.query_params.get("sort_order", "desc")
    
    # Отладочная информация
    print(f"DEBUG: sort_by={sort_by}, sort_order={sort_order}")
    print(f"DEBUG: page={page}, per_page={per_page}")
    print(f"DEBUG: URL params: {dict(request.query_params)}")
    
    # Получаем количество маршрутов из кэша
    from services.crud.purchase import get_cached_routes_count
    routes_count = get_cached_routes_count(session)
    
    # Получаем данные о доступных маршрутах из Statistics
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    from models import Statistics, AvailableRoute
    from sqlmodel import select
    
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    
    # Получаем дату последней проверки доступных маршрутов
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    
    last_check_date = None
    if available_routes_stats and available_routes_stats.updated_at:
        last_check_date = available_routes_stats.updated_at
    
    # Получаем общее количество доступных маршрутов
    total_routes = session.exec(
        select(AvailableRoute)
    ).all()
    total_count = len(total_routes)
    
    # Сортируем все маршруты согласно параметрам
    reverse_sort = sort_order == "desc"
    
    # Определяем поле для сортировки в базе данных
    sort_field_map = {
        'id': AvailableRoute.id,
        'composition': AvailableRoute.Concerts,  # Используем количество концертов как прокси для состава
        'days': AvailableRoute.Days,
        'concerts': AvailableRoute.Concerts,
        'halls': AvailableRoute.Halls,
        'genre': AvailableRoute.Genre,
        'show_time': AvailableRoute.ShowTime,
        'trans_time': AvailableRoute.TransTime,
        'wait_time': AvailableRoute.WaitTime,
        'costs': AvailableRoute.Costs,
        'comfort_score': AvailableRoute.ComfortScore,
        'comfort_level': AvailableRoute.ComfortLevel,
        'intellect_score': AvailableRoute.IntellectScore,
        'intellect_category': AvailableRoute.IntellectCategory
    }
    
    sort_field = sort_field_map.get(sort_by, AvailableRoute.Concerts)
    
    # Сортируем все маршруты
    def get_sort_value(route):
        if sort_by == 'composition':
            # Для состава используем количество концертов
            return route.Concerts
        elif sort_by == 'id':
            return route.id
        elif sort_by == 'days':
            return route.Days
        elif sort_by == 'concerts':
            return route.Concerts
        elif sort_by == 'halls':
            return route.Halls
        elif sort_by == 'genre':
            return route.Genre or ''
        elif sort_by == 'show_time':
            return route.ShowTime
        elif sort_by == 'trans_time':
            return route.TransTime
        elif sort_by == 'wait_time':
            return route.WaitTime
        elif sort_by == 'costs':
            return route.Costs
        elif sort_by == 'comfort_score':
            return route.ComfortScore or 0
        elif sort_by == 'comfort_level':
            return route.ComfortLevel or ''
        elif sort_by == 'intellect_score':
            return route.IntellectScore or 0
        elif sort_by == 'intellect_category':
            return route.IntellectCategory or ''
        else:
            return route.Concerts  # По умолчанию сортируем по количеству концертов
    
    total_routes.sort(key=get_sort_value, reverse=reverse_sort)
    
    # Вычисляем параметры пагинации
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Получаем срез для текущей страницы
    available_routes = total_routes[offset:offset + per_page]
    
    # Подготавливаем данные для таблицы
    routes_data = []
    for route in available_routes:
        # Парсим состав маршрута для отображения и сортируем номера
        concert_ids = sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()])
        concert_ids_str = [str(x) for x in concert_ids]
        
        routes_data.append({
            'id': route.id,
            'composition': ', '.join(concert_ids_str),  # Отображаем отсортированные номера концертов
            'composition_count': len(concert_ids),  # Количество концертов для сортировки
            'days': route.Days,
            'concerts': route.Concerts,
            'halls': route.Halls,
            'genre': route.Genre or 'Не указан',
            'show_time': route.ShowTime,  # Числовое значение для сортировки (в минутах)
            'show_time_display': format_time_minutes(route.ShowTime),  # Форматируем время в понятном виде
            'trans_time': route.TransTime,  # Числовое значение для сортировки (в минутах)
            'trans_time_display': format_time_minutes(route.TransTime),  # Форматируем время в понятном виде
            'wait_time': route.WaitTime,  # Числовое значение для сортировки (в минутах)
            'wait_time_display': format_time_minutes(route.WaitTime),  # Форматируем время в понятном виде
            'costs': route.Costs,  # Числовое значение для сортировки
            'costs_display': f"{route.Costs:.0f}₽",
            'comfort_score': route.ComfortScore,  # Числовое значение для сортировки
            'comfort_score_display': f"{route.ComfortScore:.1f}" if route.ComfortScore else 'Н/Д',
            'comfort_level': route.ComfortLevel or 'Н/Д',
            'intellect_score': route.IntellectScore,  # Числовое значение для сортировки
            'intellect_score_display': f"{route.IntellectScore:.1f}" if route.IntellectScore else 'Н/Д',
            'intellect_category': route.IntellectCategory or 'Н/Д'
        })
    
    # Генерируем данные для пагинации
    pagination_data = {
        'current_page': page,
        'total_pages': total_pages,
        'per_page': per_page,
        'total_count': total_count,
        'start_item': offset + 1,
        'end_item': min(offset + per_page, total_count)
    }
    
    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "view",
        "routes_count": routes_count,
        "available_routes_count": available_routes_count,
        "available_concerts_count": available_concerts_count,
        "last_check_date": last_check_date,
        "routes_data": routes_data,
        "pagination": pagination_data,
        "sort_by": sort_by,
        "sort_order": sort_order
    }
    return templates.TemplateResponse("admin_routes_view.html", context)

@home_route.get("/admin/routes/instruction", response_class=HTMLResponse)
async def admin_routes_instruction(request: Request, session=Depends(get_session)):
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
    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "instruction"
    }
    return templates.TemplateResponse("admin_routes_main.html", context)

@home_route.post("/admin/routes/upload")
async def upload_routes(request: Request, file: UploadFile = File(...), session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    # Сохраняем файл во временное место
    temp_path = ROUTES_PATH + ".uploading"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    os.replace(temp_path, ROUTES_PATH)
    # Запускаем фоновую задачу через threading (чтобы не блокировать event loop)
    thread = threading.Thread(target=process_routes_upload, args=(session, ROUTES_PATH))
    thread.start()
    return JSONResponse({"success": True, "message": "Загрузка маршрутов запущена"})

@home_route.get("/admin/routes/upload_status")
async def get_routes_upload_status():
    return JSONResponse(route_upload_status)

@home_route.get("/admin/routes/available_routes_status")
async def get_available_routes_status():
    return JSONResponse(available_routes_status)

@home_route.get("/api/routes")
async def get_routes_api(request: Request, session=Depends(get_session)):
    """
    API endpoint для ленивой загрузки маршрутов с виртуализацией.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        user = await authenticate_cookie(token)
    else:
        user = None
    user_obj = None
    if user:
        user_obj = UsersService.get_user_by_email(user, session)
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    
    # Получаем параметры
    offset = int(request.query_params.get("offset", 0))
    limit = int(request.query_params.get("limit", 100))  # Размер порции
    sort_by = request.query_params.get("sort_by", "concerts")
    sort_order = request.query_params.get("sort_order", "desc")
    
    print(f"API DEBUG: offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}")
    
    # Получаем все маршруты
    from models import AvailableRoute
    from sqlmodel import select
    
    total_routes = session.exec(select(AvailableRoute)).all()
    total_count = len(total_routes)
    
    # Сортируем все маршруты
    reverse_sort = sort_order == "desc"
    
    def get_sort_value(route):
        if sort_by == 'composition':
            return route.Concerts
        elif sort_by == 'id':
            return route.id
        elif sort_by == 'days':
            return route.Days
        elif sort_by == 'concerts':
            return route.Concerts
        elif sort_by == 'halls':
            return route.Halls
        elif sort_by == 'genre':
            return route.Genre or ''
        elif sort_by == 'show_time':
            return route.ShowTime
        elif sort_by == 'trans_time':
            return route.TransTime
        elif sort_by == 'wait_time':
            return route.WaitTime
        elif sort_by == 'costs':
            return route.Costs
        elif sort_by == 'comfort_score':
            return route.ComfortScore or 0
        elif sort_by == 'comfort_level':
            return route.ComfortLevel or ''
        elif sort_by == 'intellect_score':
            return route.IntellectScore or 0
        elif sort_by == 'intellect_category':
            return route.IntellectCategory or ''
        else:
            return route.Concerts
    
    total_routes.sort(key=get_sort_value, reverse=reverse_sort)
    
    # Получаем срез данных
    end_offset = min(offset + limit, total_count)
    available_routes = total_routes[offset:end_offset]
    
    # Подготавливаем данные
    routes_data = []
    for route in available_routes:
        concert_ids = sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()])
        concert_ids_str = [str(x) for x in concert_ids]
        
        routes_data.append({
            'id': route.id,
            'composition': ', '.join(concert_ids_str),
            'composition_count': len(concert_ids),
            'days': route.Days,
            'concerts': route.Concerts,
            'halls': route.Halls,
            'genre': route.Genre or 'Не указан',
            'show_time': route.ShowTime,
            'show_time_display': format_time_minutes(route.ShowTime),
            'trans_time': route.TransTime,
            'trans_time_display': format_time_minutes(route.TransTime),
            'wait_time': route.WaitTime,
            'wait_time_display': format_time_minutes(route.WaitTime),
            'costs': route.Costs,
            'costs_display': f"{route.Costs:.0f}₽",
            'comfort_score': route.ComfortScore,
            'comfort_score_display': f"{route.ComfortScore:.1f}" if route.ComfortScore else 'Н/Д',
            'comfort_level': route.ComfortLevel or 'Н/Д',
            'intellect_score': route.IntellectScore,
            'intellect_score_display': f"{route.IntellectScore:.1f}" if route.IntellectScore else 'Н/Д',
            'intellect_category': route.IntellectCategory or 'Н/Д'
        })
    
    return JSONResponse({
        "success": True,
        "data": routes_data,
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "has_more": end_offset < total_count,
        "sort_by": sort_by,
        "sort_order": sort_order
    })