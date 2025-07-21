from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from database.database import get_session
from database.config import get_settings
from services.crud import user as UsersService
from services.crud.purchase import get_festival_summary_stats
from config_data_path import ROUTES_PATH
import shutil
import os
import threading
import logging
from datetime import datetime
import pandas as pd
import io
from sqlmodel import select, Session
from models import Statistics, AvailableRoute, Route, Concert

settings = get_settings()
admin_routes_router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Глобальные статусы (можно вынести в отдельный модуль при необходимости)
route_upload_status = {"in_progress": False, "progress": 0, "total": 0, "added": 0, "updated": 0, "error": None}
available_routes_status = {"in_progress": False, "progress": 0, "total": 0, "available_count": 0, "total_routes": 0, "availability_percentage": 0, "error": None}

def format_time_minutes(minutes):
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

# --- Перенесённые обработчики ---

@admin_routes_router.get("/admin/routes", response_class=HTMLResponse)
async def admin_routes_redirect():
    return RedirectResponse(url="/admin/routes/upload", status_code=302)

@admin_routes_router.get("/admin/routes/upload", response_class=HTMLResponse)
async def admin_routes_upload(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)
    summary = get_festival_summary_stats(session)
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    last_check_date = available_routes_stats.updated_at if available_routes_stats and available_routes_stats.updated_at else None
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

# --- upload_status ---
@admin_routes_router.get("/admin/routes/upload_status")
async def get_routes_upload_status():
    return JSONResponse(route_upload_status)

# --- available_routes_status ---
@admin_routes_router.get("/admin/routes/available_routes_status")
async def get_available_routes_status():
    return available_routes_status

# --- upload (POST) ---
@admin_routes_router.post("/admin/routes/upload")
async def upload_routes(request: Request, file: UploadFile = File(...), session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    temp_path = ROUTES_PATH + ".uploading"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    os.replace(temp_path, ROUTES_PATH)
    # process_routes_upload и process_available_routes_check должны быть определены здесь
    def process_routes_upload(session, path):
        global route_upload_status, available_routes_status
        try:
            route_upload_status["in_progress"] = True
            route_upload_status["progress"] = 0
            route_upload_status["added"] = 0
            route_upload_status["updated"] = 0
            route_upload_status["error"] = None
            from services.crud.data_loader import load_routes_from_csv
            result = load_routes_from_csv(session, path, status_dict=route_upload_status)
            route_upload_status["added"] = result["added"]
            route_upload_status["updated"] = result["updated"]
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
            from services.crud import route_service
            from models import Route, AvailableRoute
            from sqlmodel import select
            total_routes = len(session.exec(select(Route)).all())
            available_routes_status["total_routes"] = total_routes
            available_routes_status["total"] = total_routes
            existing_count = len(session.exec(select(AvailableRoute)).all())
            if existing_count == 0:
                result = route_service.init_available_routes(session, status_dict=available_routes_status)
                available_routes_status["available_count"] = result["available_routes"]
                available_routes_status["availability_percentage"] = result.get("availability_percentage", 0)
            else:
                result = route_service.update_available_routes(session, status_dict=available_routes_status)
                available_routes_status["available_count"] = result["current_count"]
                available_routes_status["availability_percentage"] = round((result["current_count"] / total_routes * 100), 2) if total_routes > 0 else 0
            available_routes_status["progress"] = total_routes
        except Exception as e:
            available_routes_status["error"] = str(e)
            logging.error(f"Ошибка при проверке AvailableRoute: {e}")
        finally:
            available_routes_status["in_progress"] = False
    thread = threading.Thread(target=process_routes_upload, args=(session, ROUTES_PATH))
    thread.start()
    return JSONResponse({"success": True, "message": "Загрузка маршрутов запущена"})

@admin_routes_router.get("/admin/routes/concerts", response_class=HTMLResponse)
async def admin_routes_concerts(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)
    from services.crud.purchase import get_cached_routes_count
    routes_count = get_cached_routes_count(session)
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    last_check_date = available_routes_stats.updated_at if available_routes_stats and available_routes_stats.updated_at else None
    from models import Concert
    concerts = session.exec(select(Concert).order_by(Concert.id.asc())).all()
    concerts_data = []
    concerts_by_day = {}
    for concert in concerts:
        hall = concert.hall
        seats = hall.seats if hall else 100
        tickets_left = concert.tickets_left if concert.tickets_left is not None else seats
        percent_left = (tickets_left / seats * 100) if seats > 0 else 0
        if percent_left <= 10:
            status_color = '#e53935'
        elif percent_left <= 20:
            status_color = '#ffb300'
        else:
            status_color = '#43a047'
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
        if concert.datetime:
            day_key = concert.datetime.date()
            if day_key not in concerts_by_day:
                concerts_by_day[day_key] = []
            concerts_by_day[day_key].append(concert_data)
        else:
            concerts_data.append(concert_data)
    concerts_by_day_sorted = {}
    sorted_days = sorted(concerts_by_day.keys())
    for day in sorted_days:
        day_concerts = sorted(concerts_by_day[day], key=lambda x: x['datetime'])
        concerts_by_day_sorted[day] = day_concerts
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

@admin_routes_router.get("/admin/routes/view", response_class=HTMLResponse)
async def admin_routes_view(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 15))
    sort_by = request.query_params.get("sort_by", "concerts")
    sort_order = request.query_params.get("sort_order", "desc")
    from services.crud.purchase import get_cached_routes_count
    routes_count = get_cached_routes_count(session)
    from services.crud.route_service import get_cached_available_routes_count, get_cached_available_concerts_count
    available_routes_count = get_cached_available_routes_count(session)
    available_concerts_count = get_cached_available_concerts_count(session)
    available_routes_stats = session.exec(
        select(Statistics).where(Statistics.key == "available_routes_count")
    ).first()
    last_check_date = available_routes_stats.updated_at if available_routes_stats and available_routes_stats.updated_at else None
    from models import AvailableRoute
    total_routes = session.exec(select(AvailableRoute)).all()
    total_count = len(total_routes)
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
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page
    available_routes = total_routes[offset:offset + per_page]
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

@admin_routes_router.get("/admin/routes/instruction", response_class=HTMLResponse)
async def admin_routes_instruction(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)
    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "instruction"
    }
    return templates.TemplateResponse("admin_routes_main.html", context)

@admin_routes_router.get("/admin/routes/stats", response_class=HTMLResponse)
async def admin_routes_stats(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return RedirectResponse(url="/login", status_code=302)
    from services.crud.purchase import get_route_statistics_simple
    route_stats = get_route_statistics_simple(session)
    context = {
        "user": user_obj,
        "request": request,
        "active_tab": "stats",
        "route_stats": route_stats
    }
    return templates.TemplateResponse("admin_routes_main.html", context)

@admin_routes_router.get("/api/routes")
async def get_routes_api(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    offset = int(request.query_params.get("offset", 0))
    limit = int(request.query_params.get("limit", 100))
    sort_by = request.query_params.get("sort_by", "concerts")
    sort_order = request.query_params.get("sort_order", "desc")
    from models import AvailableRoute
    total_routes = session.exec(select(AvailableRoute)).all()
    total_count = len(total_routes)
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
    end_offset = min(offset + limit, total_count)
    available_routes = total_routes[offset:end_offset]
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

@admin_routes_router.post("/api/routes/stats")
async def update_route_statistics(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    try:
        from services.crud.purchase import get_route_statistics_simple
        route_stats = get_route_statistics_simple(session, force_refresh=True)
        return {
            "success": True,
            "message": "Статистика обновлена",
            "calculation_time": route_stats.get('cache_info', {}).get('calculation_time', 0)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@admin_routes_router.get("/api/routes/export-stats")
async def export_route_statistics(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    try:
        from services.crud.purchase import get_route_statistics
        output = io.BytesIO()
        route_stats = get_route_statistics(session)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
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

@admin_routes_router.get("/api/routes/stats/basic")
async def get_basic_route_statistics(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    try:
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