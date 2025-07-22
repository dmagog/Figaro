from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from database.database import get_session
from database.config import get_settings
from services.crud import user as UsersService
from sqlmodel import Session, select
from auth.authenticate import authenticate_cookie
import logging
from models import Author, Artist, Concert, Composition, ConcertCompositionLink
from models.artist import ConcertArtistLink

settings = get_settings()
api_user_router = APIRouter()

@api_user_router.post("/api/preferences")
async def save_preferences(preferences: dict, request: Request, session: Session = Depends(get_session)):
    try:
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        if token:
            try:
                user_email = await authenticate_cookie(token)
                if user_email:
                    current_user = UsersService.get_user_by_email(user_email, session)
            except Exception as e:
                pass
        if current_user:
            current_user.preferences = preferences
            session.add(current_user)
            session.commit()
            return {"success": True, "message": "Предпочтения сохранены в базе данных"}
        else:
            return {"success": True, "message": "Предпочтения сохранены в сессии (требуется авторизация для постоянного хранения)"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_user_router.get("/api/preferences")
async def get_preferences(request: Request, session: Session = Depends(get_session)):
    try:
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
            except Exception as e:
                pass
        if current_user and current_user.preferences:
            return {
                "success": True,
                "has_preferences": True,
                "preferences": current_user.preferences,
                "message": "Найдены сохраненные предпочтения"
            }
        else:
            return {
                "success": True,
                "has_preferences": False,
                "preferences": None,
                "message": "Предпочтения не найдены"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_user_router.delete("/api/preferences")
async def reset_preferences(request: Request, session: Session = Depends(get_session)):
    try:
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
            except:
                pass
        if current_user:
            current_user.preferences = None
            session.add(current_user)
            session.commit()
            return {"success": True, "message": "Предпочтения сброшены"}
        else:
            return {"success": True, "message": "Предпочтения сброшены"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_user_router.get("/api/survey-data")
async def get_survey_data(request: Request, session: Session = Depends(get_session)):
    try:
        # Получаем всех авторов
        authors = session.exec(select(Author)).all()
        # Для каждого автора считаем количество произведений
        author_ids = [a.id for a in authors]
        compositions = session.exec(select(Composition)).all()
        compositions_by_author = {}
        for comp in compositions:
            if comp.author_id:
                compositions_by_author.setdefault(comp.author_id, 0)
                compositions_by_author[comp.author_id] += 1
        # Формируем список композиторов с количеством произведений
        composers = [
            {
                'id': author.id,
                'name': author.name,
                'count': compositions_by_author.get(author.id, 0),
                'size': min(18, max(12, 12 + compositions_by_author.get(author.id, 0)))
            }
            for author in authors
        ]
        # Сортируем по количеству произведений (по убыванию)
        composers.sort(key=lambda c: c['count'], reverse=True)
        # Артисты через SQLModel
        artists = session.exec(select(Artist)).all()
        concert_links = session.exec(select(ConcertArtistLink)).all()
        concerts_by_artist = {}
        for link in concert_links:
            concerts_by_artist.setdefault(link.artist_id, 0)
            concerts_by_artist[link.artist_id] += 1
        artists_list = [
            {
                'id': artist.id,
                'name': artist.name,
                'count': concerts_by_artist.get(artist.id, 0),
                'size': min(18, max(12, 12 + concerts_by_artist.get(artist.id, 0))),
                'is_special': artist.is_special  # Добавлено поле
            }
            for artist in artists
            if concerts_by_artist.get(artist.id, 0) > 1 or artist.is_special
        ]
        # Абсолютно все артисты для поиска
        all_artists = [
            {
                'id': artist.id,
                'name': artist.name,
                'count': concerts_by_artist.get(artist.id, 0),
                'size': min(18, max(12, 12 + concerts_by_artist.get(artist.id, 0))),
                'is_special': artist.is_special
            }
            for artist in artists
        ]
        artists_list.sort(key=lambda a: a['count'], reverse=True)
        concerts_query = session.query(
            Concert.id,
            Concert.name,
            Concert.datetime
        ).order_by(
            Concert.datetime
        ).all()
        concerts = [
            {
                'id': concert.id,
                'name': f"{concert.id}. {concert.name}",
                'datetime': concert.datetime.isoformat() if concert.datetime else None
            }
            for concert in concerts_query
        ]
        # Получаем все концерты
        concerts = session.exec(select(Concert)).all()
        concerts_data = [
            {
                'id': c.id,
                'name': f"{c.id}. {c.name}",
                'datetime': c.datetime.isoformat() if c.datetime else None,
                'tickets_available': c.tickets_available
            }
            for c in concerts
        ]
        # Получаем купленные концерты пользователя (если авторизован)
        purchased_concert_ids = []
        token = request.cookies.get(settings.COOKIE_NAME)
        current_user = None
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
            except Exception:
                pass
        if current_user:
            from models.purchase import Purchase
            purchases = session.exec(select(Purchase).where(Purchase.user_external_id == current_user.external_id)).all()
            purchased_concert_ids = [p.concert_id for p in purchases]
        return {
            "success": True,
            "composers": composers,
            "artists": artists_list,
            "all_artists": all_artists,
            "concerts": concerts_data,
            "purchased_concert_ids": purchased_concert_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_user_router.get("/api/auth/check")
async def check_auth_status(request: Request, session: Session = Depends(get_session)):
    try:
        token = request.cookies.get(settings.COOKIE_NAME)
        if token:
            try:
                user_email = await authenticate_cookie(token)
                current_user = UsersService.get_user_by_email(user_email, session)
                if current_user:
                    return {
                        "authenticated": True,
                        "user": {
                            "email": current_user.email,
                            "name": current_user.name
                        }
                    }
            except:
                pass
        return {
            "authenticated": False,
            "user": None
        }
    except Exception as e:
        return {
            "authenticated": False,
            "user": None,
            "error": str(e)
        }

@api_user_router.post("/api/recommendations")
async def get_recommendations_api(request: Request, session=Depends(get_session)):
    try:
        data = await request.json()
        preferences = data.get("preferences")
        if not preferences:
            return {"success": False, "message": "Не переданы предпочтения"}
        from services import recommendation
        result = recommendation.get_recommendations(session, preferences)
        return {"success": True, "recommendations": result}
    except Exception as e:
        return {"success": False, "message": str(e)} 