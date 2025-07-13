# services/crud/purchase.py
from sqlmodel import Session, select
from models import Purchase, Concert, Hall
from typing import List, Optional
from datetime import datetime


def get_user_purchased_concerts(session: Session, user_external_id: str) -> List[Concert]:
    """
    Находит все купленные концерты пользователя по его внешнему ID
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (ClientId)
        
    Returns:
        Список объектов Concert, которые купил пользователь
    """
    # Получаем все покупки пользователя с информацией о концертах
    statement = (
        select(Concert)
        .join(Purchase, Concert.id == Purchase.concert_id)
        .where(Purchase.user_external_id == user_external_id)
        .order_by(Concert.datetime)
    )
    
    concerts = session.exec(statement).all()
    return concerts


def get_user_purchases_with_details(session: Session, user_external_id: str) -> List[dict]:
    """
    Находит все покупки пользователя с детальной информацией о концертах
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (ClientId)
        
    Returns:
        Список словарей с информацией о покупках и концертах
    """
    # Получаем покупки с информацией о концертах и залах
    statement = (
        select(Purchase, Concert, Hall)
        .join(Concert, Purchase.concert_id == Concert.id)
        .join(Hall, Concert.hall_id == Hall.id)
        .where(Purchase.user_external_id == user_external_id)
        .order_by(Concert.datetime)
    )
    
    results = session.exec(statement).all()
    
    purchases_details = []
    for purchase, concert, hall in results:
        purchases_details.append({
            'purchase_id': purchase.id,
            'external_op_id': purchase.external_op_id,
            'purchased_at': purchase.purchased_at,
            'price': purchase.price,
            'concert': {
                'id': concert.id,
                'external_id': concert.external_id,
                'name': concert.name,
                'datetime': concert.datetime,
                'duration': concert.duration,
                'genre': concert.genre,
                'price': concert.price,
                'is_family_friendly': concert.is_family_friendly,
                'link': concert.link,
                'hall': {
                    'id': hall.id,
                    'name': hall.name,
                    'address': hall.address,
                    'latitude': hall.latitude,
                    'longitude': hall.longitude
                }
            }
        })
    
    return purchases_details


def get_user_purchase_count(session: Session, user_external_id: str) -> int:
    """
    Возвращает количество покупок пользователя
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (ClientId)
        
    Returns:
        Количество покупок
    """
    statement = select(Purchase).where(Purchase.user_external_id == user_external_id)
    purchases = session.exec(statement).all()
    return len(purchases)


def get_user_purchases_by_date_range(
    session: Session, 
    user_external_id: str, 
    start_date: datetime, 
    end_date: datetime
) -> List[Concert]:
    """
    Находит покупки пользователя в заданном диапазоне дат
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (ClientId)
        start_date: Начальная дата
        end_date: Конечная дата
        
    Returns:
        Список концертов, купленных в указанном диапазоне
    """
    statement = (
        select(Concert)
        .join(Purchase, Concert.id == Purchase.concert_id)
        .where(
            Purchase.user_external_id == user_external_id,
            Concert.datetime >= start_date,
            Concert.datetime <= end_date
        )
        .order_by(Concert.datetime)
    )
    
    concerts = session.exec(statement).all()
    return concerts 