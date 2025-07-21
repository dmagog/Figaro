from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from services.crud import user as UsersService
from database.config import get_settings
from database.database import get_session
from auth.authenticate import authenticate_cookie
import logging
from sqlmodel import select, func

settings = get_settings()
admin_compositions_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_compositions_router.get("/admin/compositions", response_class=HTMLResponse)
async def admin_compositions(request: Request, session=Depends(get_session)):
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

    from models import Composition, Author, ConcertCompositionLink, Concert
    compositions = session.exec(select(Composition).order_by(Composition.name)).all()
    compositions_list = []
    for composition in compositions:
        author = session.exec(select(Author).where(Author.id == composition.author_id)).first()
        author_name = author.name if author else None
        concerts_count = session.exec(
            select(func.count(ConcertCompositionLink.concert_id))
            .where(ConcertCompositionLink.composition_id == composition.id)
        ).first() or 0
        concerts = session.exec(
            select(Concert)
            .join(ConcertCompositionLink, Concert.id == ConcertCompositionLink.concert_id)
            .where(ConcertCompositionLink.composition_id == composition.id)
            .order_by(Concert.id)
        ).all()
        concert_data = [(concert.id, concert.datetime) for concert in concerts]
        compositions_list.append({
            'id': composition.id,
            'name': composition.name,
            'author_name': author_name,
            'concerts_count': concerts_count,
            'concert_data': concert_data
        })
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