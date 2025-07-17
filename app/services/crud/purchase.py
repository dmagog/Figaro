# services/crud/purchase.py
from sqlmodel import Session, select
from models import Purchase, Concert, Hall
from typing import List, Optional
from datetime import datetime, timezone
from models import User
from sqlalchemy import func
from models.hall import Hall
from models.statistics import Statistics
from models import Route
from models.artist import Artist, ConcertArtistLink
from models.composition import Author, Composition, ConcertCompositionLink
import logging

logger = logging.getLogger(__name__)


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
        # Получаем артистов для концерта
        artists = session.exec(
            select(Artist)
            .join(ConcertArtistLink, Artist.id == ConcertArtistLink.artist_id)
            .where(ConcertArtistLink.concert_id == concert.id)
            .order_by(Artist.name)
        ).all()
        
        # Получаем произведения для концерта
        compositions = session.exec(
            select(Composition, Author)
            .join(Author, Composition.author_id == Author.id)
            .join(ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id)
            .where(ConcertCompositionLink.concert_id == concert.id)
            .order_by(Author.name, Composition.name)
        ).all()
        
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
                },
                'artists': [
                    {
                        'id': artist.id,
                        'name': artist.name,
                        'is_special': artist.is_special
                    }
                    for artist in artists
                ],
                'compositions': [
                    {
                        'id': composition.id,
                        'name': composition.name,
                        'author': {
                            'id': author.id,
                            'name': author.name
                        }
                    }
                    for composition, author in compositions
                ]
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


def get_festival_summary_stats(session: Session) -> dict:
    """
    Возвращает сводную статистику по фестивалю:
    - Количество пользователей
    - Количество концертов
    - Количество купленных билетов
    - Сумма покупок
    - Средняя заполняемость концертов (купленных билетов / концертов)
    - Количество залов
    - Количество маршрутов (из кэша)
    - Количество мероприятий офф-программы (из кэша)
    - Количество артистов
    - Количество авторов
    - Количество произведений
    """
    users_count = session.exec(select(func.count(User.id))).one()
    concerts_count = session.exec(select(func.count(Concert.id))).one()
    tickets_count = session.exec(select(func.count(Purchase.id))).one()
    total_spent = session.exec(select(func.coalesce(func.sum(Purchase.price), 0))).one()
    avg_fill = (tickets_count / concerts_count) if concerts_count else 0
    halls_count = session.exec(select(func.count(Hall.id))).one()
    routes_count = get_cached_routes_count(session)
    off_program_count = get_cached_off_program_count(session)
    artists_count = session.exec(select(func.count(Artist.id))).one()
    authors_count = session.exec(select(func.count(Author.id))).one()
    compositions_count = session.exec(select(func.count(Composition.id))).one()
    
    # Подсчитываем количество уникальных покупателей (пользователей с покупками)
    customers_count = session.exec(
        select(func.count(func.distinct(Purchase.user_external_id)))
        .where(Purchase.user_external_id.is_not(None))
    ).one()
    
    return {
        "users_count": users_count,
        "concerts_count": concerts_count,
        "tickets_count": tickets_count,
        "total_spent": total_spent,
        "avg_fill": avg_fill,
        "halls_count": halls_count,
        "routes_count": routes_count,
        "off_program_count": off_program_count,
        "artists_count": artists_count,
        "authors_count": authors_count,
        "compositions_count": compositions_count,
        "customers_count": customers_count
    } 


def get_cached_routes_count(session: Session) -> int:
    """Возвращает кэшированное количество маршрутов"""
    try:
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "routes_count")
        ).first()
        
        if stats_record:
            return stats_record.value
        else:
            # Если кэша нет, подсчитываем и создаём
            routes_count = len(session.exec(select(Route)).all())
            stats_record = Statistics(
                key="routes_count",
                value=routes_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
            session.commit()
            return routes_count
            
    except Exception as e:
        logger.error(f"Ошибка при получении кэшированного количества маршрутов: {e}")
        # В случае ошибки возвращаем 0
        return 0


def get_cached_off_program_count(session: Session) -> int:
    """Возвращает кэшированное количество мероприятий офф-программы"""
    try:
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "off_program_count")
        ).first()
        
        if stats_record:
            return stats_record.value
        else:
            # Если кэша нет, подсчитываем и создаём
            from models import OffProgram
            off_program_count = len(session.exec(select(OffProgram)).all())
            stats_record = Statistics(
                key="off_program_count",
                value=off_program_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
            session.commit()
            return off_program_count
            
    except Exception as e:
        logger.error(f"Ошибка при получении кэшированного количества мероприятий офф-программы: {e}")
        # В случае ошибки возвращаем 0
        return 0


def find_customer_route_match(session: Session, user_external_id: str) -> dict:
    """
    Находит соответствие между покупками покупателя и маршрутами.
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (ClientId)
        
    Returns:
        Словарь с информацией о найденном маршруте или причинах отсутствия соответствия
    """
    # Получаем все купленные концерты покупателя
    concerts = get_user_purchased_concerts(session, user_external_id)
    
    if not concerts:
        return {
            "found": False,
            "reason": "У покупателя нет покупок",
            "customer_concerts": [],
            "matched_routes": []
        }
    
    # Сортируем концерты по дате и получаем их ID
    customer_concert_ids = sorted([c.id for c in concerts])
    customer_concert_ids_str = ",".join(map(str, customer_concert_ids))
    
    # Получаем все маршруты
    all_routes = session.exec(select(Route)).all()
    
    # Ищем точные совпадения
    exact_matches = []
    partial_matches = []
    
    for route in all_routes:
        try:
            # Парсим состав маршрута
            route_concert_ids = sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()])
            
            # Проверяем точное совпадение
            if route_concert_ids == customer_concert_ids:
                exact_matches.append({
                    "route_id": route.id,
                    "route_composition": route.Sostav,
                    "route_days": route.Days,
                    "route_concerts": route.Concerts,
                    "route_halls": route.Halls,
                    "route_genre": route.Genre,
                    "route_show_time": route.ShowTime,
                    "route_trans_time": route.TransTime,
                    "route_wait_time": route.WaitTime,
                    "route_costs": route.Costs,
                    "route_comfort_score": route.ComfortScore,
                    "route_comfort_level": route.ComfortLevel,
                    "route_intellect_score": route.IntellectScore,
                    "route_intellect_category": route.IntellectCategory,
                    "match_type": "exact",
                    "match_percentage": 100.0
                })
            
            # Проверяем частичное совпадение (если покупатель купил подмножество концертов маршрута)
            elif set(customer_concert_ids).issubset(set(route_concert_ids)):
                match_percentage = (len(customer_concert_ids) / len(route_concert_ids)) * 100
                partial_matches.append({
                    "route_id": route.id,
                    "route_composition": route.Sostav,
                    "route_days": route.Days,
                    "route_concerts": route.Concerts,
                    "route_halls": route.Halls,
                    "route_genre": route.Genre,
                    "route_show_time": route.ShowTime,
                    "route_trans_time": route.TransTime,
                    "route_wait_time": route.WaitTime,
                    "route_costs": route.Costs,
                    "route_comfort_score": route.ComfortScore,
                    "route_comfort_level": route.ComfortLevel,
                    "route_intellect_score": route.IntellectScore,
                    "route_intellect_category": route.IntellectCategory,
                    "match_type": "partial",
                    "match_percentage": match_percentage,
                    "missing_concerts": list(set(route_concert_ids) - set(customer_concert_ids))
                })
                
        except (ValueError, AttributeError) as e:
            logger.warning(f"Ошибка при парсинге маршрута {route.id}: {e}")
            continue
    
    # Сортируем частичные совпадения по проценту совпадения
    partial_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
    
    # Формируем результат
    if exact_matches:
        return {
            "found": True,
            "match_type": "exact",
            "customer_concerts": customer_concert_ids,
            "customer_concerts_str": customer_concert_ids_str,
            "matched_routes": exact_matches,
            "best_match": exact_matches[0]
        }
    elif partial_matches:
        return {
            "found": True,
            "match_type": "partial",
            "customer_concerts": customer_concert_ids,
            "customer_concerts_str": customer_concert_ids_str,
            "matched_routes": partial_matches,
            "best_match": partial_matches[0]
        }
    else:
        return {
            "found": False,
            "reason": "Не найдено подходящих маршрутов",
            "customer_concerts": customer_concert_ids,
            "customer_concerts_str": customer_concert_ids_str,
            "matched_routes": [],
            "total_routes_checked": len(all_routes)
        }


def get_all_customers_route_matches(session: Session) -> dict:
    """
    Оптимизированная функция для получения соответствий маршрутов для всех покупателей.
    Загружает все маршруты один раз и обрабатывает всех покупателей.
    
    Returns:
        Словарь {external_id: route_match_data}
    """
    # Получаем все маршруты один раз
    all_routes = session.exec(select(Route)).all()
    
    # Создаем индекс маршрутов для быстрого поиска
    routes_by_composition = {}
    for route in all_routes:
        try:
            route_concert_ids = tuple(sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()]))
            routes_by_composition[route_concert_ids] = route
        except (ValueError, AttributeError) as e:
            logger.warning(f"Ошибка при парсинге маршрута {route.id}: {e}")
            continue
    
    # Получаем всех покупателей с их концертами
    from sqlalchemy import func
    customer_concerts = session.exec(
        select(
            Purchase.user_external_id,
            func.array_agg(Purchase.concert_id).label('concert_ids')
        )
        .group_by(Purchase.user_external_id)
    ).all()
    
    results = {}
    
    for customer_data in customer_concerts:
        external_id = str(customer_data[0])
        concert_ids = customer_data[1] if customer_data[1] else []
        
        if not concert_ids:
            results[external_id] = {
                "found": False,
                "reason": "У покупателя нет покупок",
                "customer_concerts": [],
                "customer_concerts_str": "",
                "matched_routes": []
            }
            continue
        
        # Сортируем концерты
        customer_concert_ids = sorted(concert_ids)
        customer_concert_ids_str = ",".join(map(str, customer_concert_ids))
        customer_concert_ids_tuple = tuple(customer_concert_ids)
        
        # Ищем точные совпадения
        exact_matches = []
        partial_matches = []
        
        # Проверяем точное совпадение
        if customer_concert_ids_tuple in routes_by_composition:
            route = routes_by_composition[customer_concert_ids_tuple]
            exact_matches.append({
                "route_id": route.id,
                "route_composition": route.Sostav,
                "route_days": route.Days,
                "route_concerts": route.Concerts,
                "route_halls": route.Halls,
                "route_genre": route.Genre,
                "route_show_time": route.ShowTime,
                "route_trans_time": route.TransTime,
                "route_wait_time": route.WaitTime,
                "route_costs": route.Costs,
                "route_comfort_score": route.ComfortScore,
                "route_comfort_level": route.ComfortLevel,
                "route_intellect_score": route.IntellectScore,
                "route_intellect_category": route.IntellectCategory,
                "match_type": "exact",
                "match_percentage": 100.0
            })
        
        # Проверяем частичные совпадения
        for route_concert_ids_tuple, route in routes_by_composition.items():
            if set(customer_concert_ids).issubset(set(route_concert_ids_tuple)):
                match_percentage = (len(customer_concert_ids) / len(route_concert_ids_tuple)) * 100
                partial_matches.append({
                    "route_id": route.id,
                    "route_composition": route.Sostav,
                    "route_days": route.Days,
                    "route_concerts": route.Concerts,
                    "route_halls": route.Halls,
                    "route_genre": route.Genre,
                    "route_show_time": route.ShowTime,
                    "route_trans_time": route.TransTime,
                    "route_wait_time": route.WaitTime,
                    "route_costs": route.Costs,
                    "route_comfort_score": route.ComfortScore,
                    "route_comfort_level": route.ComfortLevel,
                    "route_intellect_score": route.IntellectScore,
                    "route_intellect_category": route.IntellectCategory,
                    "match_type": "partial",
                    "match_percentage": match_percentage,
                    "missing_concerts": list(set(route_concert_ids_tuple) - set(customer_concert_ids))
                })
        
        # Сортируем частичные совпадения
        partial_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        
        # Формируем результат
        if exact_matches:
            results[external_id] = {
                "found": True,
                "match_type": "exact",
                "customer_concerts": customer_concert_ids,
                "customer_concerts_str": customer_concert_ids_str,
                "matched_routes": exact_matches,
                "best_match": exact_matches[0]
            }
        elif partial_matches:
            results[external_id] = {
                "found": True,
                "match_type": "partial",
                "customer_concerts": customer_concert_ids,
                "customer_concerts_str": customer_concert_ids_str,
                "matched_routes": partial_matches,
                "best_match": partial_matches[0]
            }
        else:
            results[external_id] = {
                "found": False,
                "reason": "Не найдено подходящих маршрутов",
                "customer_concerts": customer_concert_ids,
                "customer_concerts_str": customer_concert_ids_str,
                "matched_routes": [],
                "total_routes_checked": len(all_routes)
            }
    
    return results 