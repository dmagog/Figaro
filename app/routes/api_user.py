from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from database.database import get_session
from database.config import get_settings
from services.crud import user as UsersService
from sqlmodel import Session
from auth.authenticate import authenticate_cookie
import logging
from models import Author, Artist, Concert, Composition, ConcertCompositionLink, ConcertArtistLink

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
async def get_survey_data(session: Session = Depends(get_session)):
    try:
        composers_query = session.query(
            Author.id,
            Author.name,
            logging.getLogger().handlers,
            ).outerjoin(
            Composition, Author.id == Composition.author_id
        ).outerjoin(
            ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id
        ).outerjoin(
            Concert, ConcertCompositionLink.concert_id == Concert.id
        ).group_by(
            Author.id, Author.name
        ).order_by(
            ).all()
        composers = [
            {
                'id': comp.id,
                'name': comp.name,
                'count': getattr(comp, 'concerts_count', 0),
                'size': min(18, max(12, 12 + getattr(comp, 'concerts_count', 0)))
            }
            for comp in composers_query
        ]
        artists_query = session.query(
            Artist.id,
            Artist.name,
            logging.getLogger().handlers,
            ).outerjoin(
            ConcertArtistLink, Artist.id == ConcertArtistLink.artist_id
        ).outerjoin(
            Concert, ConcertArtistLink.concert_id == Concert.id
        ).group_by(
            Artist.id, Artist.name
        ).order_by(
            ).all()
        artists = [
            {
                'id': artist.id,
                'name': artist.name,
                'count': getattr(artist, 'concerts_count', 0),
                'size': min(18, max(12, 12 + getattr(artist, 'concerts_count', 0)))
            }
            for artist in artists_query
        ]
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
        return {
            "success": True,
            "composers": composers,
            "artists": artists,
            "concerts": concerts
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