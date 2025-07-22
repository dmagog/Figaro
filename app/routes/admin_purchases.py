from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
from auth.authenticate import authenticate_cookie
import logging
from sqlmodel import select, func  # Используем из sqlmodel

settings = get_settings()
admin_purchases_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_purchases_router.get("/admin/purchases", response_class=HTMLResponse)
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
    UserAlias = aliased(User)
    stmt = (
        select(Purchase, Concert, UserAlias, Hall)
        .join(Concert, Purchase.concert_id == Concert.id)
        .join(Hall, Concert.hall_id == Hall.id)
        .outerjoin(UserAlias, Purchase.user_external_id == UserAlias.external_id)
        .order_by(Purchase.purchased_at.desc())
    )
    purchases = session.exec(stmt).all()

    unique_users = {}
    unique_concerts = {}
    purchase_dates = [p.purchased_at for p, _, _, _ in purchases if p and p.purchased_at]
    if purchase_dates:
        min_purchase_date = min(purchase_dates).strftime('%Y-%m-%d')
        max_purchase_date = max(purchase_dates).strftime('%Y-%m-%d')
    else:
        min_purchase_date = ''
        max_purchase_date = ''
    users = session.exec(select(User)).all()
    users_with_purchases = set(
        row[0] for row in session.exec(select(Purchase.user_external_id).distinct()).all()
    )
    for u in users:
        ext_id = getattr(u, 'external_id', None)
        email = getattr(u, 'email', None)
        name = getattr(u, 'name', None)
        if ext_id and ext_id in users_with_purchases and email and email not in unique_users:
            unique_users[email] = name or email
    for p, c, u, h in purchases:
        if c and c.id not in unique_concerts:
            unique_concerts[c.id] = c.name

    from collections import defaultdict
    purchases_grouped = []
    grouped = defaultdict(list)
    for p, c, u, h in purchases:
        key = (p.user_external_id if p else None, c.id if c else None, p.purchased_at if p else None)
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
            'price': p.price if p else None,
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