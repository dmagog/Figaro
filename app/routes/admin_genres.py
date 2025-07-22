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
admin_genres_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_genres_router.get("/admin/genres", response_class=HTMLResponse)
async def admin_genres(request: Request, session=Depends(get_session)):
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

    from models.genre import Genre, ConcertGenreLink
    from models import Concert
    genres = session.exec(select(Genre).order_by(Genre.name)).all()
    genres_list = []
    for genre in genres:
        concerts_count = session.exec(
            select(func.count(ConcertGenreLink.concert_id))
            .where(ConcertGenreLink.genre_id == genre.id)
        ).first() or 0
        concerts = session.exec(
            select(Concert)
            .join(ConcertGenreLink, Concert.id == ConcertGenreLink.concert_id)
            .where(ConcertGenreLink.genre_id == genre.id)
            .order_by(Concert.id)
        ).all()
        concert_data = [(concert.id, concert.datetime) for concert in concerts]
        genres_list.append({
            'id': genre.id,
            'name': genre.name,
            'description': genre.description,
            'concerts_count': concerts_count,
            'concert_data': concert_data
        })
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