from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
from auth.authenticate import authenticate_cookie
import logging
from sqlalchemy import select, func
import asyncio
import sys
sys.path.append("../../bot")
from bot.utils import send_telegram_message

settings = get_settings()
admin_users_router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_user_field(u, field):
    if isinstance(u, tuple):
        u = u[0]
    return getattr(u, field, None)

def normalize_id(val):
    return ''.join(filter(str.isdigit, str(val))).strip() if val is not None else ''

@admin_users_router.get("/admin/users", response_class=HTMLResponse)
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

    from models import Purchase
    users = session.exec(select(UsersService.User)).all()
    user_stats = {}
    for u in users:
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
        print('USER:', user_info)
        ext_id = get_user_field(u, 'external_id')
        user_id = get_user_field(u, 'id')
        if not user_id:
            continue
        if not ext_id:
            user_stats[user_id] = {"count": 0, "spent": 0, "unique_concerts": 0, "tickets": 0}
            continue
        purchases = session.exec(select(Purchase).where(Purchase.user_external_id == str(ext_id))).all()
        unique_concerts = len(set(getattr(p, 'concert_id', None) for p in purchases))
        tickets = len(purchases)
        spent = sum(getattr(p, 'price', 0) or 0 for p in purchases)
        user_stats[user_id] = {"count": tickets, "spent": spent, "unique_concerts": unique_concerts, "tickets": tickets}

    users_with_purchases_count = sum(1 for u in users if get_user_field(u, 'id') and user_stats.get(get_user_field(u, 'id'), {}).get('count', 0) > 0)

    # Загружаем информацию о маршрутах пользователей
    route_matches = {}
    try:
        from models import CustomerRouteMatch, Route
        routes = session.exec(select(Route)).all()
        routes_by_id = {getattr(route, 'id', None): route for route in routes if getattr(route, 'id', None) is not None}
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

@admin_users_router.get("/admin/telegram", response_class=HTMLResponse)
async def admin_telegram_page(request: Request, session=Depends(get_session)):
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
    context = {"request": request}
    return templates.TemplateResponse("admin_telegram.html", context)

@admin_users_router.post("/admin/send-telegram")
async def send_telegram(request: Request, session=Depends(get_session)):
    form = await request.form()
    # Получаем данные из формы
    user_ids = form.getlist("user_ids")
    user_id = form.get("user_id")
    telegram_id = form.get("telegram_id")
    message = form.get("message")
    markdown = form.get("markdown") == '1'
    file = form.get("file")
    file_path = None
    file_type = None
    # Сохраняем файл, если он есть
    if file and hasattr(file, 'filename') and file.filename:
        import tempfile
        suffix = '.' + file.filename.split('.')[-1] if '.' in file.filename else ''
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            file_path = tmp.name
        # Определяем тип файла
        if file.content_type.startswith('image/'):
            file_type = 'photo'
        else:
            file_type = 'document'
    # Собираем список telegram_id для рассылки
    telegram_ids = []
    if user_ids:
        for uid in user_ids:
            if not uid or not str(uid).isdigit():
                continue
            user = session.exec(select(UsersService.User).where(UsersService.User.id == int(uid))).first()
            if user and hasattr(user, 'telegram_id') and user.telegram_id:
                telegram_ids.append(user.telegram_id)
    if telegram_id:
        telegram_ids.append(telegram_id)
    if user_id and not telegram_ids:
        if str(user_id).isdigit():
            user = session.exec(select(UsersService.User).where(UsersService.User.id == int(user_id))).first()
            if user and hasattr(user, 'telegram_id') and user.telegram_id:
                telegram_ids.append(user.telegram_id)
    if not telegram_ids:
        return JSONResponse({"success": False, "error": "Не выбран ни один пользователь с Telegram ID"}, status_code=400)
    # Отправляем сообщение каждому
    errors = []
    for tg_id in set(telegram_ids):
        try:
            await send_telegram_message(
                tg_id,
                text=message,
                file_path=file_path,
                file_type=file_type,
                parse_mode='Markdown' if markdown else None
            )
        except Exception as e:
            errors.append(str(e))
    # Удаляем временный файл
    if file_path:
        import os
        try:
            os.remove(file_path)
        except Exception:
            pass
    if errors:
        return JSONResponse({"success": False, "error": "; ".join(errors)}, status_code=500)
    return JSONResponse({"success": True}) 