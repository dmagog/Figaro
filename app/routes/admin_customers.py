from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
import logging
from sqlmodel import select, func
from auth.authenticate import authenticate_cookie
from models.purchase import Customer
from typing import Optional

settings = get_settings()
admin_customers_router = APIRouter()
templates = Jinja2Templates(directory="templates")

def normalize_id(val):
    return ''.join(filter(str.isdigit, str(val))).strip() if val is not None else ''

@admin_customers_router.get("/admin/customers", response_class=HTMLResponse)
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
    purchases = session.exec(select(Purchase)).all()
    concerts = session.exec(select(Concert)).all()
    concerts_by_id = {c.id: c for c in concerts if c.id is not None}
    users = session.exec(select(User)).all()
    users_by_external = {normalize_id(u.external_id): u for u in users if u.external_id is not None}

    # Группируем покупки по user_external_id
    purchases_by_external = {}
    for p in purchases:
        purchases_by_external.setdefault(str(p.user_external_id), []).append(p)

    # Загружаем маршруты, если нужно
    route_matches = {}
    if load_routes:
        try:
            matches = session.exec(select(CustomerRouteMatch)).all()
            for match in matches:
                route_matches[str(match.user_external_id)] = match
        except Exception as e:
            logging.warning(f"Ошибка при получении маршрутов: {e}")
            route_matches = {}

    customers = []
    for ext_id, user_purchases in purchases_by_external.items():
        total_spent = sum((p.price or 0) for p in user_purchases)
        unique_concerts = set(p.concert_id for p in user_purchases)
        unique_days = set(
            concerts_by_id[p.concert_id].datetime.date()
            for p in user_purchases
            if p.concert_id in concerts_by_id and getattr(concerts_by_id[p.concert_id], 'datetime', None)
        )
        user = users_by_external.get(normalize_id(ext_id))
        name = user.name if user else None
        email = user.email if user else None
        role = user.role if user else None
        is_superuser = user.is_superuser if user else None
        route_match = route_matches.get(normalize_id(ext_id))
        if route_match:
            route_match_dict = route_match.dict()
            # Добавляем best_match для шаблона
            if route_match.found and route_match.best_route_id:
                route_match_dict['best_match'] = {
                    'route_id': route_match.best_route_id,
                    'match_percentage': route_match.match_percentage,
                }
            else:
                route_match_dict['best_match'] = None
        else:
            route_match_dict = {
                "found": False,
                "reason": "Нет данных о маршруте",
                "customer_concerts": [],
                "matched_routes": [],
                "best_match": None
            }
        customers.append(Customer(
            user_external_id=ext_id,
            name=name,
            email=email,
            role=role,
            is_superuser=is_superuser,
            total_purchases=len(user_purchases),
            total_spent=total_spent,
            unique_concerts=len(unique_concerts),
            unique_days=len(unique_days),
            route_match=route_match_dict
        ))
    # Сортировка: 1) наличие покупателя (зарегистрированные выше), 2) уникальных концертов (убыв.), 3) дней фестиваля (убыв.)
    customers.sort(key=lambda c: (
        1 if c.name else 0,  # зарегистрированные выше
        c.unique_concerts,
        c.unique_days
    ), reverse=True)
    return templates.TemplateResponse("admin_customers.html", {"request": request, "customers": customers}) 