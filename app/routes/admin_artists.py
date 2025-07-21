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
admin_artists_router = APIRouter()
templates = Jinja2Templates(directory="templates")

@admin_artists_router.get("/admin/artists", response_class=HTMLResponse)
async def admin_artists(request: Request, session=Depends(get_session)):
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

    from models import Artist, ConcertArtistLink, Concert
    # Получаем всех артистов ORM-объектами
    artists = session.exec(select(Artist).order_by(Artist.name)).all()
    # Для каждого артиста считаем количество концертов и собираем данные о концертах
    artists_list = []
    for artist in artists:
        concerts_count = session.exec(
            select(func.count(ConcertArtistLink.concert_id))
            .where(ConcertArtistLink.artist_id == artist.id)
        ).first() or 0
        concerts = session.exec(
            select(Concert)
            .join(ConcertArtistLink, Concert.id == ConcertArtistLink.concert_id)
            .where(ConcertArtistLink.artist_id == artist.id)
            .order_by(Concert.id)
        ).all()
        concert_data = [(concert.id, concert.datetime) for concert in concerts]
        concert_data.sort(key=lambda x: x[0])
        artists_list.append({
            'id': artist.id,
            'name': artist.name,
            'is_special': artist.is_special,
            'concerts_count': concerts_count,
            'concert_data': concert_data
        })
    total_artists = len(artists_list)
    special_artists = sum(1 for artist in artists_list if artist['is_special'])
    artists_with_concerts = sum(1 for artist in artists_list if artist['concerts_count'] > 0)
    context = {
        "user": user_obj,
        "request": request,
        "artists": artists_list,
        "total_artists": total_artists,
        "special_artists": special_artists,
        "artists_with_concerts": artists_with_concerts
    }
    return templates.TemplateResponse("admin_artists.html", context) 