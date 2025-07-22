from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List, Optional
from datetime import datetime
from database.database import get_session
from services.crud import purchase as PurchaseService
from auth.authenticate import authenticate_cookie
from models import User

# Создаем экземпляр роутера
purchase_route = APIRouter()


@purchase_route.get("/purchases/concerts/{user_external_id}")
async def get_user_purchased_concerts(
    user_external_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(authenticate_cookie)
):
    """
    Получает все купленные концерты пользователя
    
    Args:
        user_external_id: Внешний ID пользователя (ClientId)
        session: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Список купленных концертов
    """
    try:
        concerts = PurchaseService.get_user_purchased_concerts(session, user_external_id)
        
        # Преобразуем в JSON-совместимый формат
        concerts_data = []
        for concert in concerts:
            concert_data = {
                "id": concert.id,
                "external_id": concert.external_id,
                "name": concert.name,
                "datetime": concert.datetime.isoformat(),
                "duration": str(concert.duration),
                "genre": concert.genre,
                "price": concert.price,
                "is_family_friendly": concert.is_family_friendly,
                "tickets_available": concert.tickets_available,
                "link": concert.link,
                "hall": {
                    "id": concert.hall.id,
                    "name": concert.hall.name,
                    "address": concert.hall.address,
                    "latitude": concert.hall.latitude,
                    "longitude": concert.hall.longitude
                } if concert.hall else None
            }
            concerts_data.append(concert_data)
        
        return {
            "user_external_id": user_external_id,
            "total_concerts": len(concerts_data),
            "concerts": concerts_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении покупок: {str(e)}"
        )


@purchase_route.get("/purchases/details/{user_external_id}")
async def get_user_purchases_with_details(
    user_external_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(authenticate_cookie)
):
    """
    Получает детальную информацию о покупках пользователя
    
    Args:
        user_external_id: Внешний ID пользователя (ClientId)
        session: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Детальная информация о покупках
    """
    try:
        purchases = PurchaseService.get_user_purchases_with_details(session, user_external_id)
        
        # Преобразуем datetime в строки для JSON
        for purchase in purchases:
            purchase['purchased_at'] = purchase['purchased_at'].isoformat()
            purchase['concert']['datetime'] = purchase['concert']['datetime'].isoformat()
            purchase['concert']['duration'] = str(purchase['concert']['duration'])
        
        return {
            "user_external_id": user_external_id,
            "total_purchases": len(purchases),
            "purchases": purchases
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении деталей покупок: {str(e)}"
        )


@purchase_route.get("/purchases/count/{user_external_id}")
async def get_user_purchase_count(
    user_external_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(authenticate_cookie)
):
    """
    Получает количество покупок пользователя
    
    Args:
        user_external_id: Внешний ID пользователя (ClientId)
        session: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Количество покупок
    """
    try:
        count = PurchaseService.get_user_purchase_count(session, user_external_id)
        
        return {
            "user_external_id": user_external_id,
            "purchase_count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при подсчете покупок: {str(e)}"
        )


@purchase_route.get("/purchases/date-range/{user_external_id}")
async def get_user_purchases_by_date_range(
    user_external_id: str,
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    session: Session = Depends(get_session),
    current_user: User = Depends(authenticate_cookie)
):
    """
    Получает покупки пользователя в заданном диапазоне дат
    
    Args:
        user_external_id: Внешний ID пользователя (ClientId)
        start_date: Начальная дата
        end_date: Конечная дата
        session: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Список концертов в указанном диапазоне дат
    """
    try:
        # Парсим даты
        start_datetime = datetime.fromisoformat(f"{start_date}T00:00:00")
        end_datetime = datetime.fromisoformat(f"{end_date}T23:59:59")
        
        concerts = PurchaseService.get_user_purchases_by_date_range(
            session, user_external_id, start_datetime, end_datetime
        )
        
        # Преобразуем в JSON-совместимый формат
        concerts_data = []
        for concert in concerts:
            concert_data = {
                "id": concert.id,
                "external_id": concert.external_id,
                "name": concert.name,
                "datetime": concert.datetime.isoformat(),
                "duration": str(concert.duration),
                "genre": concert.genre,
                "price": concert.price,
                "is_family_friendly": concert.is_family_friendly,
                "tickets_available": concert.tickets_available,
                "link": concert.link,
                "hall": {
                    "id": concert.hall.id,
                    "name": concert.hall.name,
                    "address": concert.hall.address,
                    "latitude": concert.hall.latitude,
                    "longitude": concert.hall.longitude
                } if concert.hall else None
            }
            concerts_data.append(concert_data)
        
        return {
            "user_external_id": user_external_id,
            "start_date": start_date,
            "end_date": end_date,
            "total_concerts": len(concerts_data),
            "concerts": concerts_data
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверный формат даты: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении покупок по датам: {str(e)}"
        )


@purchase_route.get("/purchases/summary/{user_external_id}")
async def get_user_purchase_summary(
    user_external_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(authenticate_cookie)
):
    """
    Получает сводную информацию о покупках пользователя
    
    Args:
        user_external_id: Внешний ID пользователя (ClientId)
        session: Сессия базы данных
        current_user: Текущий аутентифицированный пользователь
        
    Returns:
        Сводная информация о покупках
    """
    try:
        # Получаем все покупки с деталями
        purchases = PurchaseService.get_user_purchases_with_details(session, user_external_id)
        
        if not purchases:
            return {
                "user_external_id": user_external_id,
                "total_purchases": 0,
                "total_spent": 0,
                "unique_concerts": 0,
                "unique_halls": 0,
                "genres": [],
                "summary": "У пользователя нет покупок"
            }
        
        # Анализируем данные
        total_spent = sum(p.get('price', 0) or 0 for p in purchases)
        unique_concerts = len(set(p['concert']['id'] for p in purchases))
        unique_halls = len(set(p['concert']['hall']['id'] for p in purchases if p['concert']['hall']))
        genres = list(set(p['concert']['genre'] for p in purchases if p['concert']['genre']))
        
        # Группируем по жанрам
        genre_stats = {}
        for purchase in purchases:
            genre = purchase['concert']['genre']
            if genre:
                if genre not in genre_stats:
                    genre_stats[genre] = 0
                genre_stats[genre] += 1
        
        return {
            "user_external_id": user_external_id,
            "total_purchases": len(purchases),
            "total_spent": total_spent,
            "unique_concerts": unique_concerts,
            "unique_halls": unique_halls,
            "genres": genres,
            "genre_stats": genre_stats,
            "summary": f"Пользователь посетил {unique_concerts} уникальных концертов в {unique_halls} залах"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении сводки покупок: {str(e)}"
        ) 