from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, status
from database.config import get_settings
from services.crud import user as UserService
from services.crud import purchase as PurchaseService
from auth.authenticate import authenticate_cookie
from datetime import datetime, timedelta
from app.routes.user import get_all_festival_days_with_visit_status, get_user_route_sheet, get_user_characteristics
import logging
from uuid import uuid4
from models.user import TelegramLinkCode
from sqlmodel import select
settings = get_settings()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)

async def profile_page_logic(request, session):
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    try:
        user_email = await authenticate_cookie(token)
        if not user_email:
            return RedirectResponse(url="/login", status_code=302)
        current_user = UserService.get_user_by_email(user_email, session)
        if not current_user:
            return RedirectResponse(url="/login", status_code=302)
        user_external_id = current_user.external_id
        if not user_external_id:
            basic_route_sheet = {
                "summary": {"total_concerts": 0, "total_days": 0, "total_halls": 0, "total_genres": 0, "total_spent": 0},
                "match": {"found": False, "match_type": "no_external_id", "reason": "Для анализа маршрутов требуется external_id", "match_percentage": 0.0, "total_routes_checked": 0, "customer_concerts": [], "best_route": None},
                "concerts_by_day": {}
            }
            context = {
                "request": request,
                "user": current_user,
                "concerts": [],
                "purchase_summary": {"total_purchases": 0, "total_spent": 0, "total_concerts": 0, "unique_halls": 0, "genres": []},
                "route_sheet": basic_route_sheet,
                "characteristics": {},
                "festival_days": [],
                "telegram_linked": False,
                "telegram_id": None,
                "telegram_link_code": None,
                "telegram_link_code_expires": None
            }
            return templates.TemplateResponse("profile.html", context)
        purchases = PurchaseService.get_user_purchases_with_details(session, user_external_id)
        purchase_summary = {
            "total_purchases": len(purchases),
            "total_spent": sum(p.get('price', 0) or 0 for p in purchases),
            "total_concerts": len(set(p['concert']['id'] for p in purchases)),
            "unique_halls": len(set(p['concert']['hall']['id'] for p in purchases if p['concert']['hall'])),
            "genres": list(set(p['concert']['genre'] for p in purchases if p['concert']['genre']))
        }
        unique_concerts = {}
        for purchase in purchases:
            concert_id = purchase['concert']['id']
            if concert_id not in unique_concerts:
                unique_concerts[concert_id] = {'concert': purchase['concert'], 'tickets_count': 1, "total_spent": purchase.get('price', 0) or 0}
            else:
                unique_concerts[concert_id]['tickets_count'] += 1
                unique_concerts[concert_id]['total_spent'] += purchase.get('price', 0) or 0
        concerts_for_template = []
        for concert_id, concert_data in unique_concerts.items():
            try:
                concert_copy = concert_data.copy()
                if isinstance(concert_data['concert']['datetime'], str):
                    concert_copy['concert']['datetime'] = datetime.fromisoformat(concert_data['concert']['datetime'])
                else:
                    concert_copy['concert']['datetime'] = concert_data['concert']['datetime']
                duration_str = concert_data['concert']['duration']
                if isinstance(duration_str, (int, float)):
                    concert_copy['concert']['duration'] = timedelta(seconds=duration_str)
                elif isinstance(duration_str, str) and ':' in duration_str:
                    parts = duration_str.split(':')
                    if len(parts) >= 2:
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        concert_copy['concert']['duration'] = timedelta(hours=hours, minutes=minutes)
                else:
                    concert_copy['concert']['duration'] = duration_str
                concerts_for_template.append(concert_copy)
            except Exception as e:
                concerts_for_template.append(concert_data)
                continue
        concerts_for_template.sort(key=lambda x: x['concert']['datetime'] if x['concert']['datetime'] else datetime.min)
        day_to_index = {}
        for i, concert in enumerate(concerts_for_template):
            dt = concert['concert']['datetime']
            if dt:
                day = dt.date()
                if day not in day_to_index:
                    day_to_index[day] = len(day_to_index) + 1
                concert['concert_day_index'] = day_to_index[day]
            else:
                concert['concert_day_index'] = 0
        for i, concert_data in enumerate(concerts_for_template, 1):
            concert_data['concert_number'] = i
        festival_days_data = get_all_festival_days_with_visit_status(session, concerts_for_template)
        try:
            route_sheet_data = get_user_route_sheet(session, user_external_id, concerts_for_template, festival_days_data)
        except Exception as e:
            route_sheet_data = {"summary": {"total_concerts": len(concerts_for_template), "total_days": 0, "total_halls": 0, "total_genres": 0, "total_spent": 0}, "match": {"found": False, "match_type": "error", "reason": f"Ошибка при анализе маршрутов: {str(e)}", "match_percentage": 0.0, "total_routes_checked": 0, "customer_concerts": [], "best_route": None}, "concerts_by_day": {}}
        try:
            characteristics_data = get_user_characteristics(session, user_external_id, concerts_for_template)
        except Exception as e:
            characteristics_data = {"total_concerts": 0, "halls": [], "genres": [], "artists": [], "composers": [], "compositions": []}
        telegram_linked = current_user.telegram_id is not None
        telegram_id = current_user.telegram_id
        now = datetime.utcnow()
        link_code_obj = session.exec(
            select(TelegramLinkCode)
            .where(TelegramLinkCode.user_id == current_user.id)
            .where(TelegramLinkCode.expires_at > now)
        ).first()
        telegram_link_code = link_code_obj.code if link_code_obj else None
        telegram_link_code_expires = link_code_obj.expires_at if link_code_obj else None
        context = {
            "request": request,
            "user": current_user,
            "concerts": concerts_for_template,
            "purchase_summary": purchase_summary,
            "route_sheet": route_sheet_data,
            "characteristics": characteristics_data,
            "festival_days": festival_days_data,
            "telegram_linked": telegram_linked,
            "telegram_id": telegram_id,
            "telegram_link_code": telegram_link_code,
            "telegram_link_code_expires": telegram_link_code_expires
        }
        return templates.TemplateResponse("profile.html", context)
    except Exception as e:
        return RedirectResponse(url="/", status_code=302)

async def set_external_id_logic(request, session):
    token = request.cookies.get(settings.COOKIE_NAME)
    user_email = None
    if token:
        user_email = await authenticate_cookie(token)
    if not user_email:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user = UserService.get_user_by_email(user_email, session)
    if not user or not getattr(user, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    data = await request.json()
    new_external_id = data.get('external_id')
    if not new_external_id:
        return JSONResponse({"success": False, "error": "Некорректные данные"}, status_code=400)
    user.external_id = new_external_id
    session.add(user)
    session.commit()
    session.refresh(user)
    return JSONResponse({"success": True, "external_id": user.external_id})

async def debug_user_external_id_logic(email, session):
    try:
        user = UserService.get_user_by_email(email, session)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return {
            "email": user.email,
            "external_id": user.external_id,
            "id": user.id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def set_user_external_id_logic(email, external_id, session):
    try:
        user = UserService.get_user_by_email(email, session)
        if not user:
            return {"error": "User not found"}
        user.external_id = external_id
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "success": True,
            "email": user.email,
            "external_id": user.external_id
        }
    except Exception as e:
        return {"error": str(e)}

async def debug_user_purchases_logic(external_id, session):
    try:
        purchases = PurchaseService.get_user_purchases_with_details(session, external_id)
        return {
            "external_id": external_id,
            "purchases_count": len(purchases),
            "purchases": purchases[:3]
        }
    except Exception as e:
        return {"error": str(e)}

async def generate_telegram_link_code_logic(request, session):
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user_email = await authenticate_cookie(token)
    if not user_email:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user = UserService.get_user_by_email(user_email, session)
    if not user:
        return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=404)
    # Удаляем старые коды
    session.exec(
        select(TelegramLinkCode).where(
            TelegramLinkCode.user_id == user.id
        )
    ).delete()
    # Генерируем новый код
    code = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    link_code = TelegramLinkCode(user_id=user.id, code=code, created_at=datetime.utcnow(), expires_at=expires_at)
    session.add(link_code)
    session.commit()
    session.refresh(link_code)
    return {"success": True, "code": code, "expires_at": expires_at.isoformat()} 