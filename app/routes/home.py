from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
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
from datetime import datetime
from models import OffProgram, EventFormat, Artist, Author, Composition, ConcertArtistLink, ConcertCompositionLink
import io
from sqlmodel import Session, select
from models.user import User
from typing import Optional
from .admin_customers import admin_customers_router
from .admin_users import admin_users_router
from .admin_purchases import admin_purchases_router
from .admin_concerts import admin_concerts_router
from .admin_halls import admin_halls_router
from .admin_offprogram import admin_offprogram_router
from .admin_artists import admin_artists_router
from .admin_authors import admin_authors_router
from .admin_compositions import admin_compositions_router
from .admin_genres import admin_genres_router
from .admin_routes import admin_routes_router
from .api_user import api_user_router

def get_field(obj, field):
    if isinstance(obj, dict):
        return obj.get(field)
    if hasattr(obj, '_mapping') and field in obj._mapping:
        return obj._mapping[field]
    return getattr(obj, field, None)

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
        session: Сессия базы данных

    Returns:
        HTMLResponse: HTML страница с контекстом пользователя
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    current_user = None
    
    if token:
        try:
            user_email = await authenticate_cookie(token)
            current_user = UsersService.get_user_by_email(user_email, session)
        except:
            pass  # Пользователь не авторизован

    context = {
        "login": current_user is not None,
        "request": request,
        "user": current_user
    }

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

    # Добавляем заглушки для новых разделов
    alerts = {
        "critical": 0,
        "notifications": 2
    }
    
    telegram_stats = {
        "sent": 15
    }

    context = {
        "user": user_obj,
        "request": request,
        "summary": summary,
        "routes_count": routes_count,
        "alerts": alerts,
        "telegram_stats": telegram_stats
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
    users = session.exec(select(UsersService.User)).all()
    # Для каждого пользователя считаем покупки и сумму трат
    from models import Purchase
    from sqlalchemy import func
    user_stats = {}
    for u in users:
        # Безопасное логирование без чувствительных данных
        user_info = {
            'id': getattr(u, 'id', None),
            'name': getattr(u, 'name', None),
            'email': getattr(u, 'email', None),
            'role': getattr(u, 'role', None),
            'is_active': getattr(u, 'is_active', None),
            'is_superuser': getattr(u, 'is_superuser', None),
            'external_id': getattr(u, 'external_id', None),
            'created_at': getattr(u, 'created_at', None),
            'updated_at': getattr(u, 'updated_at', None)
        }
        print('USER:', user_info)  # DEBUG
        ext_id = get_user_field(u, 'external_id')
        user_id = get_user_field(u, 'id')
        if not user_id:
            continue  # пропускаем пользователей без id
        if not ext_id:
            user_stats[user_id] = {"count": 0, "spent": 0, "unique_concerts": 0, "tickets": 0}
            continue
        # Все покупки пользователя
        purchases = session.exec(select(Purchase).where(Purchase.user_external_id == str(ext_id))).all()
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
            best_route = None
            if match.found and match.best_route_id:
                try:
                    best_route = routes_by_id.get(match.best_route_id)
                    if best_route:
                        found_matches += 1
                except Exception as e:
                    logging.warning(f"Ошибка при получении маршрута {match.best_route_id}: {e}")
                    best_route = None
            route_matches[str(match.user_external_id)] = {
                "found": match.found,
                "match_type": match.match_type,
                "reason": match.reason,
                "customer_concerts": match.customer_concerts.split(',') if match.customer_concerts else [],
                "customer_concerts_str": match.customer_concerts,
                "matched_routes": [],
                "best_match": {
                    "route_id": match.best_route_id,
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
                    "match_type": match.match_type,
                    "match_percentage": match.match_percentage
                } if match.found else None,
                "total_routes_checked": match.total_routes_checked
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

    from models import Hall, Concert, Purchase, HallTransition
    from sqlalchemy import select, func
    halls = session.exec(select(Hall)).all()
    concerts = session.exec(select(Concert)).all()
    
    # Получаем переходы между залами
    transitions = session.exec(select(HallTransition)).all()

    # Для расчёта средней заполняемости по каждому залу
    concerts_by_hall = {}
    for c in concerts:
        concerts_by_hall.setdefault(get_field(c, 'hall_id'), []).append(c)

    # Используем новый сервис билетов
    from services.crud.tickets import get_tickets_left

    # Считаем количество концертов и мест по каждому залу
    hall_stats = {get_field(h, 'id'): {"concerts": 0, "seats": get_field(h, 'seats'), "tickets_sold": 0, "available_concerts": 0} for h in halls}
    for c in concerts:
        if get_field(c, 'hall_id') in hall_stats:
            hall_stats[get_field(c, 'hall_id')]["concerts"] += 1
            hall_stats[get_field(c, 'hall_id')]["seats"] = hall_stats[get_field(c, 'hall_id')]["seats"] or 0
            tickets_left = get_tickets_left(get_field(c, 'id'))
            if tickets_left > 0:
                hall_stats[get_field(c, 'hall_id')]["available_concerts"] += 1

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
        stats = hall_stats[get_field(h, 'id')]
        fill_percent = (stats["tickets_sold"] / (stats["seats"] * stats["concerts"]) * 100) if stats["seats"] and stats["concerts"] else 0
        # Средняя заполняемость по всем концертам этого зала
        fill_percents = []
        for c in concerts_by_hall.get(get_field(h, 'id'), []):
            seats = get_field(h, 'seats') or 0
            if seats > 0:
                # Считаем количество купленных билетов для этого концерта
                from models import Purchase
                tickets_row = session.exec(select(func.count(Purchase.id)).where(Purchase.concert_id == get_field(c, 'id'))).scalars().first()
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
    hall_ids = [get_field(h["hall"], 'id') for h in halls_data]
    
    # Формируем данные о переходах между залами в виде матрицы
    halls_by_id = {get_field(h, 'id'): h for h in halls}
    hall_names = [get_field(h, 'name') for h in halls]
    
    # Создаем матрицу переходов
    transitions_matrix = {}
    for from_hall in halls:
        transitions_matrix[get_field(from_hall, 'name')] = {}
        for to_hall in halls:
            transitions_matrix[get_field(from_hall, 'name')][get_field(to_hall, 'name')] = None
    
    # Заполняем матрицу данными о переходах
    for transition in transitions:
        from_hall = halls_by_id.get(get_field(transition, 'from_hall_id'))
        to_hall = halls_by_id.get(get_field(transition, 'to_hall_id'))
        if from_hall and to_hall:
            transitions_matrix[get_field(from_hall, 'name')][get_field(to_hall, 'name')] = get_field(transition, 'transition_time')
    
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
    """
    Страница с инструкцией по работе с маршрутами.
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
        return RedirectResponse(url="/login", status_code=302)

    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "instruction"
    }
    return templates.TemplateResponse("admin_routes_main.html", context)

@home_route.get("/admin/routes/stats", response_class=HTMLResponse)
async def admin_routes_stats(request: Request, session=Depends(get_session)):
    """
    Страница статистики популярности маршрутов.
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
        return RedirectResponse(url="/login", status_code=302)

    # Получаем статистику маршрутов (использует простую версию)
    from services.crud.purchase import get_route_statistics_simple
    route_stats = get_route_statistics_simple(session)

    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "stats",
        "route_stats": route_stats
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
    """
    Получение статуса проверки AvailableRoute.
    """
    return available_routes_status

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

@home_route.get("/admin/artists", response_class=HTMLResponse)
async def admin_artists(request: Request, session=Depends(get_session)):
    """
    Страница управления артистами. Доступ только для суперадмина.
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

    # Получаем всех артистов с количеством концертов и номерами концертов
    from sqlalchemy import func
    artists_data = session.exec(
        select(
            Artist,
            func.count(ConcertArtistLink.concert_id).label('concerts_count')
        )
        .outerjoin(ConcertArtistLink, Artist.id == ConcertArtistLink.artist_id)
        .group_by(Artist.id)
        .order_by(Artist.name)
    ).all()

    # Получаем номера концертов для каждого артиста
    from models import Concert
    artist_concerts = {}
    for artist_data in artists_data:
        artist = artist_data[0]
        
        concerts = session.exec(
            select(Concert)
            .join(ConcertArtistLink, Concert.id == ConcertArtistLink.concert_id)
            .where(ConcertArtistLink.artist_id == artist.id)
            .order_by(Concert.id)
        ).all()
        # Извлекаем ID и даты из объектов
        concert_data = []
        for concert in concerts:
            if hasattr(concert, '_mapping'):
                # Это Row объект с _mapping
                if 'Concert' in concert._mapping:
                    # Если есть ключ 'Concert', то это объект Concert
                    concert_obj = concert._mapping['Concert']
                    concert_data.append((concert_obj.id, concert_obj.datetime))
                else:
                    # Иначе берем по индексам
                    concert_data.append((concert[0], concert[1]))
            else:
                # Это может быть объект Concert или tuple
                if hasattr(concert, 'id') and hasattr(concert, 'datetime'):
                    concert_data.append((concert.id, concert.datetime))
                else:
                    concert_data.append((concert[0], concert[1]))
        
        # Сортируем по ID концерта
        concert_data.sort(key=lambda x: x[0])
        artist_concerts[artist.id] = concert_data

    # Подготавливаем данные для отображения
    artists_list = []
    for artist_data in artists_data:
        artist = artist_data[0]
        concerts_count = artist_data[1]
        
        artists_list.append({
            'id': artist.id,
            'name': artist.name,
            'is_special': artist.is_special,
            'concerts_count': concerts_count,
            'concert_data': artist_concerts.get(artist.id, [])
        })

    # Статистика
    total_artists = len(artists_list)
    special_artists = sum(1 for artist in artists_list if artist['is_special'])
    artists_with_concerts = sum(1 for artist in artists_list if artist['concerts_count'] > 0)

    context = {
        "user": user_obj,
        "request": request,
        "artists": artists_list,
        "total_artists": total_artists,
        "special_artists": special_artists,
        "artists_with_concerts": artists_with_concerts
    }
    return templates.TemplateResponse("admin_artists.html", context)


@home_route.get("/admin/authors", response_class=HTMLResponse)
async def admin_authors(request: Request, session=Depends(get_session)):
    """
    Страница управления авторами. Доступ только для суперадмина.
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

    # Получаем всех авторов с количеством произведений и концертов
    from sqlalchemy import func
    authors_data = session.exec(
        select(
            Author,
            func.count(Composition.id).label('compositions_count'),
            func.count(ConcertCompositionLink.concert_id.distinct()).label('concerts_count')
        )
        .outerjoin(Composition, Author.id == Composition.author_id)
        .outerjoin(ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id)
        .group_by(Author.id)
        .order_by(Author.name)
    ).all()

    # Подготавливаем данные для отображения
    authors_list = []
    for author_data in authors_data:
        author = author_data[0]
        compositions_count = author_data[1]
        concerts_count = author_data[2]
        
        authors_list.append({
            'id': author.id,
            'name': author.name,
            'compositions_count': compositions_count,
            'concerts_count': concerts_count
        })

    # Статистика
    total_authors = len(authors_list)
    authors_with_compositions = sum(1 for author in authors_list if author['compositions_count'] > 0)
    authors_with_concerts = sum(1 for author in authors_list if author['concerts_count'] > 0)

    context = {
        "user": user_obj,
        "request": request,
        "authors": authors_list,
        "total_authors": total_authors,
        "authors_with_compositions": authors_with_compositions,
        "authors_with_concerts": authors_with_concerts
    }
    return templates.TemplateResponse("admin_authors.html", context)


@home_route.get("/admin/compositions", response_class=HTMLResponse)
async def admin_compositions(request: Request, session=Depends(get_session)):
    """
    Страница управления произведениями. Доступ только для суперадмина.
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

    # Получаем все произведения с информацией об авторах и количестве концертов
    from sqlalchemy import func
    compositions_data = session.exec(
        select(
            Composition,
            Author.name.label('author_name'),
            func.count(ConcertCompositionLink.concert_id).label('concerts_count')
        )
        .join(Author, Composition.author_id == Author.id)
        .outerjoin(ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id)
        .group_by(Composition.id, Author.name)
        .order_by(Author.name, Composition.name)
    ).all()

    # Получаем номера концертов для каждого произведения
    from models import Concert
    composition_concerts = {}
    for comp_data in compositions_data:
        composition = comp_data[0]
        concerts = session.exec(
            select(Concert)
            .join(ConcertCompositionLink, Concert.id == ConcertCompositionLink.concert_id)
            .where(ConcertCompositionLink.composition_id == composition.id)
            .order_by(Concert.id)
        ).all()
        concert_data = []
        for concert in concerts:
            if hasattr(concert, '_mapping'):
                # Это Row объект с _mapping
                if 'Concert' in concert._mapping:
                    # Если есть ключ 'Concert', то это объект Concert
                    concert_obj = concert._mapping['Concert']
                    concert_data.append((concert_obj.id, concert_obj.datetime))
                else:
                    # Иначе берем по индексам
                    concert_data.append((concert[0], concert[1]))
            else:
                # Это может быть объект Concert или tuple
                if hasattr(concert, 'id') and hasattr(concert, 'datetime'):
                    concert_data.append((concert.id, concert.datetime))
                else:
                    concert_data.append((concert[0], concert[1]))
        composition_concerts[composition.id] = concert_data

    # Подготавливаем данные для отображения
    compositions_list = []
    for comp_data in compositions_data:
        composition = comp_data[0]
        author_name = comp_data[1]
        concerts_count = comp_data[2]
        
        compositions_list.append({
            'id': composition.id,
            'name': composition.name,
            'author_name': author_name,
            'concerts_count': concerts_count,
            'concert_data': composition_concerts.get(composition.id, [])
        })

    # Статистика
    total_compositions = len(compositions_list)
    compositions_with_concerts = sum(1 for comp in compositions_list if comp['concerts_count'] > 0)
    total_performances = sum(comp['concerts_count'] for comp in compositions_list)

    context = {
        "user": user_obj,
        "request": request,
        "compositions": compositions_list,
        "total_compositions": total_compositions,
        "compositions_with_concerts": compositions_with_concerts,
        "total_performances": total_performances
    }
    return templates.TemplateResponse("admin_compositions.html", context)


@home_route.get("/admin/genres", response_class=HTMLResponse)
async def admin_genres(request: Request, session=Depends(get_session)):
    """
    Страница управления жанрами. Доступ только для суперадмина.
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

    # Получаем все жанры с информацией о количестве концертов
    from sqlalchemy import func
    from models.genre import Genre, ConcertGenreLink
    from models import Concert
    
    genres_data = session.exec(
        select(
            Genre,
            func.count(ConcertGenreLink.concert_id).label('concerts_count')
        )
        .outerjoin(ConcertGenreLink, Genre.id == ConcertGenreLink.genre_id)
        .group_by(Genre.id)
        .order_by(Genre.name)
    ).all()

    # Получаем номера концертов для каждого жанра
    genre_concerts = {}
    for genre_data in genres_data:
        genre = genre_data[0]
        concerts = session.exec(
            select(Concert)
            .join(ConcertGenreLink, Concert.id == ConcertGenreLink.concert_id)
            .where(ConcertGenreLink.genre_id == genre.id)
            .order_by(Concert.id)
        ).all()
        concert_data = []
        for concert in concerts:
            if hasattr(concert, '_mapping'):
                # Это Row объект с _mapping
                if 'Concert' in concert._mapping:
                    # Если есть ключ 'Concert', то это объект Concert
                    concert_obj = concert._mapping['Concert']
                    concert_data.append((concert_obj.id, concert_obj.datetime))
                else:
                    # Иначе берем по индексам
                    concert_data.append((concert[0], concert[1]))
            else:
                # Это может быть объект Concert или tuple
                if hasattr(concert, 'id') and hasattr(concert, 'datetime'):
                    concert_data.append((concert.id, concert.datetime))
                else:
                    concert_data.append((concert[0], concert[1]))
        genre_concerts[genre.id] = concert_data

    # Подготавливаем данные для отображения
    genres_list = []
    for genre_data in genres_data:
        genre = genre_data[0]
        concerts_count = genre_data[1]
        
        genres_list.append({
            'id': genre.id,
            'name': genre.name,
            'description': genre.description,
            'concerts_count': concerts_count,
            'concert_data': genre_concerts.get(genre.id, [])
        })

    # Статистика
    total_genres = len(genres_list)
    genres_with_concerts = sum(1 for genre in genres_list if genre['concerts_count'] > 0)
    total_performances = sum(genre['concerts_count'] for genre in genres_list)

    context = {
        "user": user_obj,
        "request": request,
        "genres": genres_list,
        "total_genres": total_genres,
        "genres_with_concerts": genres_with_concerts,
        "total_performances": total_performances
    }
    return templates.TemplateResponse("admin_genres.html", context)

@home_route.post("/api/routes/stats")
async def update_route_statistics(request: Request, session=Depends(get_session)):
    """
    Обновление статистики маршрутов.
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
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    try:
        # Принудительно обновляем статистику (простая версия)
        from services.crud.purchase import get_route_statistics_simple
        route_stats = get_route_statistics_simple(session, force_refresh=True)
        
        return {
            "success": True, 
            "message": "Статистика обновлена",
            "calculation_time": route_stats.get('cache_info', {}).get('calculation_time', 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@home_route.get("/api/routes/export-stats")
async def export_route_statistics(request: Request, session=Depends(get_session)):
    """
    Экспорт статистики маршрутов в Excel.
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
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    try:
        from services.crud.purchase import get_route_statistics
        from fastapi.responses import StreamingResponse
        import io
        
        # Получаем статистику
        route_stats = get_route_statistics(session)
        
        # Создаем Excel файл
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист с общей статистикой
            overview_data = {
                'Метрика': ['Всего покупок', 'Уникальных маршрутов', 'Активных покупателей', 'Средняя популярность (%)'],
                'Значение': [
                    route_stats.get('total_purchases', 0),
                    route_stats.get('unique_routes', 0),
                    route_stats.get('active_users', 0),
                    route_stats.get('avg_popularity', 0)
                ]
            }
            pd.DataFrame(overview_data).to_excel(writer, sheet_name='Общая статистика', index=False)
            
            # Лист с популярными маршрутами
            if route_stats.get('popular_routes'):
                popular_routes_data = []
                for route in route_stats['popular_routes']:
                    popular_routes_data.append({
                        'ID маршрута': route.get('route_id'),
                        'Название': route.get('route_name'),
                        'Количество покупок': route.get('purchase_count'),
                        'Процент от общих покупок': route.get('percentage'),
                        'Последняя покупка': route.get('last_purchase'),
                        'Статус': route.get('status')
                    })
                pd.DataFrame(popular_routes_data).to_excel(writer, sheet_name='Популярные маршруты', index=False)
            
            # Лист со статистикой по дням
            if route_stats.get('daily_stats'):
                daily_stats_data = []
                for day_stat in route_stats['daily_stats']:
                    daily_stats_data.append({
                        'День': day_stat.get('day'),
                        'Дата': day_stat.get('date'),
                        'Покупок': day_stat.get('purchases'),
                        'Маршрутов': day_stat.get('routes'),
                        'Популярность (%)': day_stat.get('popularity')
                    })
                pd.DataFrame(daily_stats_data).to_excel(writer, sheet_name='Статистика по дням', index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=route_statistics_{datetime.now().strftime('%Y%m%d')}.xlsx"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")

@home_route.get("/api/routes/stats/basic")
async def get_basic_route_statistics(request: Request, session=Depends(get_session)):
    """
    Получение базовой статистики маршрутов (простая версия).
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
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    try:
        # Используем простую версию статистики
        from services.crud.purchase import get_route_statistics_simple
        route_stats = get_route_statistics_simple(session)
        
        return {
            "success": True,
            "data": {
                "total_purchases": route_stats['total_purchases'],
                "unique_routes": route_stats['unique_routes'],
                "active_users": route_stats['active_users'],
                "matched_customers": route_stats['matched_customers'],
                "unmatched_customers": route_stats['unmatched_customers'],
                "match_percentage": (route_stats['matched_customers'] / route_stats['active_users'] * 100) if route_stats['active_users'] > 0 else 0
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@home_route.post("/api/preferences")
async def save_preferences(
    preferences: dict,
    request: Request,
    session: Session = Depends(get_session)
):
    """Сохранение предпочтений пользователя"""
    try:
        print(f"DEBUG: Saving preferences: {preferences}")
        print(f"DEBUG: Request headers: {dict(request.headers)}")
        print(f"DEBUG: Request cookies: {request.cookies}")
        
        # Получаем токен из cookie
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        
        print(f"DEBUG: Token from cookie: {token}")
        print(f"DEBUG: Cookie name setting: {settings.COOKIE_NAME}")
        
        if token:
            try:
                print(f"DEBUG: Attempting to authenticate token...")
                user_email = await authenticate_cookie(token)
                print(f"DEBUG: Authenticated user email: {user_email}")
                
                if user_email:
                    current_user = UsersService.get_user_by_email(user_email, session)
                    print(f"DEBUG: Found user: {current_user.email if current_user else 'None'}")
                    if current_user:
                        print(f"DEBUG: User ID: {current_user.id}")
                        print(f"DEBUG: User preferences before: {current_user.preferences}")
                else:
                    print(f"DEBUG: No user email returned from authentication")
            except Exception as e:
                print(f"DEBUG: Authentication error: {e}")
                import traceback
                print(f"DEBUG: Authentication traceback: {traceback.format_exc()}")
                pass  # Пользователь не авторизован
        else:
            print(f"DEBUG: No token found in cookies")
        
        if current_user:
            # Обновляем предпочтения авторизованного пользователя
            print(f"DEBUG: Updating preferences for user {current_user.email}")
            current_user.preferences = preferences
            session.add(current_user)
            session.commit()
            print(f"DEBUG: Preferences saved successfully")
            print(f"DEBUG: User preferences after: {current_user.preferences}")
            return {"success": True, "message": "Предпочтения сохранены в базе данных"}
        else:
            print(f"DEBUG: No authenticated user, saving to session")
            # Для неавторизованных пользователей сохраняем в сессии
            # В реальном приложении здесь можно использовать Redis или другой механизм
            # Пока просто возвращаем успех
            return {"success": True, "message": "Предпочтения сохранены в сессии (требуется авторизация для постоянного хранения)"}
    except Exception as e:
        print(f"DEBUG: Error in save_preferences: {e}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@home_route.get("/api/preferences")
async def get_preferences(
    request: Request,
    session: Session = Depends(get_session)
):
    """Получение сохраненных предпочтений пользователя"""
    try:
        # Получаем токен из cookie
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        
        print(f"DEBUG: Token from cookie: {token}")
        
        if token:
            try:
                user_email = await authenticate_cookie(token)
                print(f"DEBUG: Authenticated user email: {user_email}")
                current_user = UsersService.get_user_by_email(user_email, session)
                print(f"DEBUG: Found user: {current_user.email if current_user else 'None'}")
                if current_user:
                    print(f"DEBUG: User preferences: {current_user.preferences}")
            except Exception as e:
                print(f"DEBUG: Authentication error: {e}")
                pass  # Пользователь не авторизован
        
        if current_user and current_user.preferences:
            print(f"DEBUG: Returning preferences for user {current_user.email}")
            return {
                "success": True, 
                "has_preferences": True,
                "preferences": current_user.preferences,
                "message": "Найдены сохраненные предпочтения"
            }
        else:
            print(f"DEBUG: No preferences found for user {current_user.email if current_user else 'anonymous'}")
            return {
                "success": True, 
                "has_preferences": False,
                "preferences": None,
                "message": "Предпочтения не найдены"
            }
    except Exception as e:
        print(f"DEBUG: Error in get_preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@home_route.delete("/api/preferences")
async def reset_preferences(
    request: Request,
    session: Session = Depends(get_session)
):
    """Сброс предпочтений пользователя"""
    try:
        # Получаем токен из cookie
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
            except:
                pass  # Пользователь не авторизован
        
        if current_user:
            # Сбрасываем предпочтения авторизованного пользователя
            current_user.preferences = None
            session.add(current_user)
            session.commit()
            return {"success": True, "message": "Предпочтения сброшены"}
        else:
            return {"success": True, "message": "Предпочтения сброшены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@home_route.get("/api/auth/check")
async def check_auth_status(
    request: Request,
    session: Session = Depends(get_session)
):
    """Проверка статуса авторизации пользователя"""
    try:
        # Получаем токен из cookie
        token = request.cookies.get(settings.COOKIE_NAME)
        
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
                if current_user:
                    return {
                        "authenticated": True,
                        "user": {
                            "email": current_user.email,
                            "name": current_user.name
                        }
                    }
            except:
                pass
        
        return {
            "authenticated": False,
            "user": None
        }
    except Exception as e:
        return {
            "authenticated": False,
            "user": None,
            "error": str(e)
        }

@home_route.post("/api/recommendations")
async def get_recommendations_api(
    request: Request,
    session=Depends(get_session)
):
    """API для получения рекомендованных маршрутов по preferences (анкета)"""
    try:
        data = await request.json()
        preferences = data.get("preferences")
        print(f"DEBUG: Получены предпочтения: {preferences}")
        
        if not preferences:
            print("DEBUG: Предпочтения не переданы")
            return {"success": False, "message": "Не переданы предпочтения"}
        
        from services import recommendation
        result = recommendation.get_recommendations(session, preferences)
        print(f"DEBUG: Результат рекомендаций: {result}")
        
        return {"success": True, "recommendations": result}
    except Exception as e:
        print(f"DEBUG: Ошибка в get_recommendations_api: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}


@home_route.get("/admin/api/dashboard-stats")
async def get_dashboard_stats(request: Request, session=Depends(get_session)):
    """API для получения статистики дашборда"""
    try:
        # Проверяем авторизацию
        token = request.cookies.get(settings.COOKIE_NAME)
        if token:
            user = await authenticate_cookie(token)
        else:
            user = None

        user_obj = None
        if user:
            user_obj = UsersService.get_user_by_email(user, session)
        if not user_obj or not getattr(user_obj, 'is_superuser', False):
            raise HTTPException(status_code=403, detail="Доступ запрещен")

        # Получаем базовую статистику
        from models import User, Purchase, Concert, Hall
        from sqlalchemy import func
        
        users_count = session.exec(select(func.count(User.id))).first()
        # customers_count = 0  # Модель Customer не существует
        tickets_count = session.exec(select(func.count(Purchase.id))).first()
        concerts_count = session.exec(select(func.count(Concert.id))).first()
        halls_count = session.exec(select(func.count(Hall.id))).first()
        
        # Статистика Telegram
        telegram_users = session.exec(select(func.count(User.id)).where(User.telegram_id.is_not(None))).first()
        
        # Алерты (заглушка для демонстрации)
        alerts = {
            "critical": 0,  # Здесь будет логика проверки критических ситуаций
            "notifications": 2
        }
        
        # Статистика Telegram рассылок
        telegram_stats = {
            "sent": 15,  # Здесь будет реальная статистика
            "users": telegram_users or 0
        }
        
        return {
            "users_count": users_count,
            "customers_count": 0,  # Модель Customer не существует
            "tickets_count": tickets_count,
            "concerts_count": concerts_count,
            "halls_count": halls_count,
            "alerts": alerts,
            "telegram_stats": telegram_stats
        }
        
    except Exception as e:
        print(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


@home_route.get("/admin/api/alerts")
async def get_alerts(request: Request, session=Depends(get_session)):
    """API для получения алертов"""
    try:
        # Проверяем авторизацию
        token = request.cookies.get(settings.COOKIE_NAME)
        if token:
            user = await authenticate_cookie(token)
        else:
            user = None

        user_obj = None
        if user:
            user_obj = UsersService.get_user_by_email(user, session)
        if not user_obj or not getattr(user_obj, 'is_superuser', False):
            raise HTTPException(status_code=403, detail="Доступ запрещен")

        alerts = []
        
        # Проверяем концерты с низкой заполняемостью
        from models import Concert
        low_fill_concerts = session.exec(
            select(Concert)
            .where(Concert.available_seats < 10)
            .limit(5)
        ).all()
        
        for concert in low_fill_concerts:
            alerts.append({
                "type": "critical",
                "message": f"Низкая заполняемость: {concert.name} - {concert.available_seats} мест",
                "concert_id": concert.id
            })
        
        # Проверяем проблемы с Telegram ботом
        # Здесь можно добавить проверку статуса бота
        
        return {
            "critical": alerts,
            "notifications": []
        }
        
    except Exception as e:
        print(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения алертов")


@home_route.get("/admin/telegram/stats", response_class=HTMLResponse)
async def admin_telegram_stats(request: Request, session=Depends(get_session)):
    """Страница статистики Telegram (заглушка)"""
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
        "request": request
    }
    return templates.TemplateResponse("admin_telegram_stats.html", context)


@home_route.get("/admin/notifications/settings", response_class=HTMLResponse)
async def admin_notifications_settings(request: Request, session=Depends(get_session)):
    """Страница настроек уведомлений (заглушка)"""
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
        "request": request
    }
    return templates.TemplateResponse("admin_notifications_settings.html", context)





home_route.include_router(admin_customers_router)
home_route.include_router(admin_users_router)
home_route.include_router(admin_purchases_router)
home_route.include_router(admin_concerts_router)
home_route.include_router(admin_halls_router)
home_route.include_router(admin_offprogram_router)
home_route.include_router(admin_artists_router)
home_route.include_router(admin_authors_router)
home_route.include_router(admin_compositions_router)
home_route.include_router(admin_genres_router)
home_route.include_router(admin_routes_router)
home_route.include_router(api_user_router)