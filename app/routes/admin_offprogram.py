from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
from auth.authenticate import authenticate_cookie
import logging
from sqlalchemy import select, func
from datetime import datetime

settings = get_settings()
admin_offprogram_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_offprogram_router.get("/admin/offprogram", response_class=HTMLResponse)
async def admin_offprogram(request: Request, session=Depends(get_session)):
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

    from models import OffProgram
    events = session.exec(
        select(OffProgram)
        .order_by(OffProgram.event_date, OffProgram.event_name)
    ).all()

    events_data = []
    for event in events:
        event_data = event
        event_long = event_data.event_long
        event_date = event_data.event_date
        event_format = event_data.format
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