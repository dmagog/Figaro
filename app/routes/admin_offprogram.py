from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database.database import get_session
from database.config import get_settings
from services.crud import user as UsersService
from sqlmodel import select
from datetime import datetime
import logging
from models import OffProgram
from auth.authenticate import authenticate_cookie

settings = get_settings()
admin_offprogram_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_offprogram_router.get("/admin/offprogram", response_class=HTMLResponse)
async def admin_offprogram(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    events = session.exec(
        select(OffProgram)
        .order_by(OffProgram.event_date, OffProgram.event_name)
    ).all()
    events_data = []
    for event in events:
        event_data = event
        event_long = event.event_long
        event_date = event.event_date
        event_format = event.format
        duration_display = event_long
        if event_long and event_long != "00:00:00":
            try:
                time_parts = event_long.split(':')
                if len(time_parts) >= 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    if hours > 0 and minutes > 0:
                        duration_display = f"{hours}ч {minutes}м"
                    elif hours > 0:
                        duration_display = f"{hours}ч"
                    else:
                        duration_display = f"{minutes}м"
            except:
                duration_display = event_long
        events_data.append({
            'id': event_data.id,
            'event_num': event_data.event_num,
            'event_name': event_data.event_name,
            'description': event_data.description or 'Описание отсутствует',
            'event_date': event_date.isoformat() if event_date else None,
            'event_date_display': event_date.strftime('%d.%m.%Y %H:%M') if event_date else 'Н/Д',
            'event_long': event_long,
            'duration_display': duration_display,
            'hall_name': event_data.hall_name,
            'format': event_format.value if event_format else 'Не указан',
            'recommend': str(event_data.recommend).lower() in ('1', 'true', 'yes', 'да'),
            'link': event_data.link
        })
    total_events = len(events_data)
    recommended_events = sum(1 for event in events_data if event['recommend'])
    formats_stats = {}
    for event in events_data:
        format_name = event['format']
        formats_stats[format_name] = formats_stats.get(format_name, 0) + 1
    halls_stats = {}
    for event in events_data:
        hall_name = event['hall_name']
        halls_stats[hall_name] = halls_stats.get(hall_name, 0) + 1
    halls = sorted(list(set(event['hall_name'] for event in events_data if event['hall_name'])))
    formats = sorted(list(set(event['format'] for event in events_data if event['format'])))
    events_by_day = {}
    for event in events_data:
        if event['event_date']:
            try:
                day = datetime.fromisoformat(event['event_date']).date()
                if day not in events_by_day:
                    events_by_day[day] = []
                events_by_day[day].append(event)
            except Exception as e:
                continue
    sorted_days = sorted(events_by_day.keys())
    for day in sorted_days:
        events_by_day[day].sort(key=lambda x: x['event_date'])
    event_days = sorted_days
    context = {
        "user": user_obj,
        "request": request,
        "events": events_data,
        "events_by_day": events_by_day,
        "sorted_days": sorted_days,
        "total_events": total_events,
        "recommended_events": recommended_events,
        "formats_stats": formats_stats,
        "halls_stats": halls_stats,
        "halls": halls,
        "formats": formats,
        "event_days": event_days
    }
    return templates.TemplateResponse("admin_offprogram.html", context)

@admin_offprogram_router.post("/api/offprogram/toggle-recommend")
async def toggle_offprogram_recommend(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user = await authenticate_cookie(token) if token else None
    user_obj = UsersService.get_user_by_email(user, session) if user else None
    if not user_obj or not getattr(user_obj, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещен"}, status_code=403)
    try:
        data = await request.json()
        event_id = data.get('event_id')
        recommend = data.get('recommend')
        if event_id is None or recommend is None:
            return JSONResponse({"success": False, "error": "Отсутствуют обязательные параметры"}, status_code=400)
        event = session.exec(select(OffProgram).where(OffProgram.id == event_id)).first()
        if not event:
            return JSONResponse({"success": False, "error": "Мероприятие не найдено"}, status_code=404)
        event_data = event
        if isinstance(recommend, bool):
            new_recommend = recommend
        elif isinstance(recommend, str):
            new_recommend = recommend.lower() in ('true', '1', 'yes', 'да')
        elif isinstance(recommend, int):
            new_recommend = bool(recommend)
        else:
            new_recommend = bool(recommend)
        event_data.recommend = new_recommend
        session.add(event_data)
        session.commit()
        from services.crud.data_loader import update_off_program_count_cache
        update_off_program_count_cache(session)
        return JSONResponse({
            "success": True,
            "message": "Состояние рекомендации обновлено",
            "data": {
                "event_id": event_id,
                "recommend": new_recommend
            }
        })
    except Exception as e:
        session.rollback()
        logging.error(f"Ошибка при обновлении рекомендации: {str(e)}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Ошибка при обновлении: {str(e)}"
        }, status_code=500) 