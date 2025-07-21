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
admin_authors_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_authors_router.get("/admin/authors", response_class=HTMLResponse)
async def admin_authors(request: Request, session=Depends(get_session)):
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

    from models import Author, Composition, ConcertCompositionLink
    authors = session.exec(select(Author).order_by(Author.name)).all()
    authors_list = []
    for author in authors:
        compositions_count = session.exec(
            select(func.count(Composition.id))
            .where(Composition.author_id == author.id)
        ).first() or 0
        concerts_count = session.exec(
            select(func.count(ConcertCompositionLink.concert_id.distinct()))
            .join(Composition, Composition.id == ConcertCompositionLink.composition_id)
            .where(Composition.author_id == author.id)
        ).first() or 0
        authors_list.append({
            'id': author.id,
            'name': author.name,
            'compositions_count': compositions_count,
            'concerts_count': concerts_count
        })
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