# services/crud/purchase.py
from sqlmodel import Session, select
from models import Purchase, Concert, Hall, AvailableRoute
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from models.user import User
from sqlalchemy import func
from models.hall import Hall
from models.statistics import Statistics
from models import Route
from models.artist import Artist, ConcertArtistLink
from models.composition import Author, Composition, ConcertCompositionLink
from models.genre import Genre
import logging
import time

logger = logging.getLogger(__name__)

# Кэш для статистики маршрутов
_route_statistics_cache = None
_route_statistics_cache_time = None
_route_statistics_cache_ttl = 300  # 5 минут


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
    genres_count = session.exec(select(func.count(Genre.id))).one()
    
    # Подсчитываем количество уникальных покупателей (пользователей с покупками)
    customers_count = session.exec(
        select(func.count(func.distinct(Purchase.user_external_id)))
        .where(Purchase.user_external_id.is_not(None))
    ).one()
    
    # Подсчитываем доступные концерты (с билетами)
    available_concerts_count = session.exec(
        select(func.count(Concert.id))
        .where(Concert.tickets_available == True)
        .where((Concert.tickets_left > 0) | (Concert.tickets_left.is_(None)))
    ).one()
    
    # Подсчитываем доступные маршруты
    available_routes_count = session.exec(select(func.count(AvailableRoute.id))).one()
    
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
        "genres_count": genres_count,
        "customers_count": customers_count,
        "available_concerts_count": available_concerts_count,
        "available_routes_count": available_routes_count
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
    Находит соответствия маршрутов для всех покупателей
    
    Returns:
        Словарь с информацией о соответствии маршрутов
    """
    # Получаем всех пользователей с покупками
    users_with_purchases = session.exec(
        select(User.external_id)
        .join(Purchase, User.external_id == Purchase.user_external_id)
        .distinct()
    ).all()
    
    results = {
        'total_customers': len(users_with_purchases),
        'matched_customers': 0,
        'unmatched_customers': 0,
        'customers_data': []
    }
    
    for user_external_id in users_with_purchases:
        customer_data = find_customer_route_match(session, user_external_id)
        results['customers_data'].append(customer_data)
        
        if customer_data['found']: # Changed from customer_data['route_match'] to customer_data['found']
            results['matched_customers'] += 1
        else:
            results['unmatched_customers'] += 1
    
    return results


def get_route_statistics(session: Session, force_refresh: bool = False) -> dict:
    """
    Возвращает статистику популярности маршрутов среди покупателей
    Использует кэширование для улучшения производительности
    
    Args:
        session: Сессия базы данных
        force_refresh: Принудительно обновить кэш
        
    Returns:
        Словарь со статистикой маршрутов
    """
    global _route_statistics_cache, _route_statistics_cache_time
    
    # Проверяем кэш
    current_time = time.time()
    if (not force_refresh and 
        _route_statistics_cache is not None and 
        _route_statistics_cache_time is not None and
        current_time - _route_statistics_cache_time < _route_statistics_cache_ttl):
        
        logger.info("Возвращаем статистику маршрутов из кэша")
        return _route_statistics_cache
    
    logger.info("Начинаем расчет статистики маршрутов...")
    start_time = time.time()
    
    try:
        # Получаем данные о соответствии маршрутов для всех покупателей
        customers_data = get_all_customers_route_matches(session)
        
        if not customers_data['customers_data']:
            result = {
                'total_purchases': 0,
                'unique_routes': 0,
                'active_users': 0,
                'avg_popularity': 0,
                'popular_routes': [],
                'daily_stats': [],
                'matched_customers': 0,
                'unmatched_customers': 0,
                'cache_info': {
                    'cached': False,
                    'calculation_time': 0
                }
            }
            
            # Сохраняем в кэш
            _route_statistics_cache = result
            _route_statistics_cache_time = current_time
            
            return result
        
        # Подсчитываем популярность маршрутов
        route_popularity = {}
        route_details = {}
        route_last_purchase = {}
        
        # Получаем все покупки для определения дат
        purchases_query = (
            select(Purchase.user_external_id, Purchase.concert_id, Purchase.purchased_at)
            .order_by(Purchase.purchased_at)
        )
        purchases = session.exec(purchases_query).all()
        
        # Создаем словарь последних покупок пользователей
        user_last_purchase = {}
        for purchase in purchases:
            user_id = purchase.user_external_id
            if user_id not in user_last_purchase or purchase.purchased_at > user_last_purchase[user_id]:
                user_last_purchase[user_id] = purchase.purchased_at
        
        # Анализируем данные о соответствии маршрутов
        for customer_data in customers_data['customers_data']:
            if customer_data['found'] and customer_data['matched_routes']:
                # Берем лучший маршрут для этого покупателя
                best_match = customer_data['best_match']
                route_id = best_match['route_id']
                
                # Увеличиваем счетчик популярности маршрута
                if route_id not in route_popularity:
                    route_popularity[route_id] = 0
                    route_details[route_id] = best_match
                route_popularity[route_id] += 1
                
                # Обновляем дату последней покупки для маршрута
                # Находим пользователя по его концертам
                for purchase in purchases:
                    user_concerts = [p.concert_id for p in purchases if p.user_external_id == purchase.user_external_id]
                    if set(user_concerts) == set(customer_data['customer_concerts']):
                        user_id = purchase.user_external_id
                        if user_id in user_last_purchase:
                            if route_id not in route_last_purchase or user_last_purchase[user_id] > route_last_purchase[route_id]:
                                route_last_purchase[route_id] = user_last_purchase[user_id]
                        break
        
        # Сортируем маршруты по популярности
        sorted_routes = sorted(route_popularity.items(), key=lambda x: x[1], reverse=True)
        
        # Подготавливаем данные для топ маршрутов
        popular_routes = []
        total_customers = customers_data['total_customers']
        
        for route_id, customer_count in sorted_routes[:20]:  # Топ 20 маршрутов
            route_detail = route_details[route_id]
            percentage = (customer_count / total_customers * 100) if total_customers > 0 else 0
            
            popular_routes.append({
                'route_id': route_id,
                'route_name': f"Маршрут {route_id}",
                'purchase_count': customer_count,
                'percentage': percentage,
                'last_purchase': route_last_purchase.get(route_id),
                'status': 'available',  # Все найденные маршруты доступны
                'route_details': {
                    'days': route_detail.get('route_days'),
                    'concerts': route_detail.get('route_concerts'),
                    'halls': route_detail.get('route_halls'),
                    'genre': route_detail.get('route_genre'),
                    'comfort_score': route_detail.get('route_comfort_score'),
                    'intellect_score': route_detail.get('route_intellect_score')
                }
            })
        
        # Статистика по дням (упрощенная версия для ускорения)
        daily_stats = []
        
        # Получаем уникальные даты концертов
        concert_dates = session.exec(
            select(Concert.datetime)
            .distinct()
            .order_by(Concert.datetime)
        ).all()
        
        # Группируем концерты по дням
        concerts_by_day = {}
        for concert_datetime in concert_dates:
            if concert_datetime:
                day_date = concert_datetime.date()
                if day_date not in concerts_by_day:
                    concerts_by_day[day_date] = []
                concerts_by_day[day_date].append(concert_datetime)
        
        # Анализируем статистику по дням
        for day_num, (day_date, day_concerts) in enumerate(concerts_by_day.items(), 1):
            day_concert_ids = [c.id for c in day_concerts]
            day_purchases = 0
            day_routes = set()
            
            # Считаем покупки и маршруты для этого дня
            for customer_data in customers_data['customers_data']:
                if customer_data['found']:
                    # Проверяем, есть ли у покупателя концерты в этот день
                    customer_day_concerts = [cid for cid in customer_data['customer_concerts'] if cid in day_concert_ids]
                    if customer_day_concerts:
                        day_purchases += len(customer_day_concerts)
                        
                        # Добавляем маршрут в статистику дня
                        if customer_data['matched_routes']:
                            best_match = customer_data['best_match']
                            day_routes.add(best_match['route_id'])
            
            # Вычисляем популярность дня
            total_purchases = sum(route_popularity.values())
            day_popularity = (day_purchases / total_purchases * 100) if total_purchases > 0 else 0
            
            daily_stats.append({
                'day': day_num,
                'date': day_date,
                'purchases': day_purchases,
                'routes': len(day_routes),
                'popularity': day_popularity
            })
        
        calculation_time = time.time() - start_time
        logger.info(f"Статистика маршрутов рассчитана за {calculation_time:.2f} секунд")
        
        result = {
            'total_purchases': len(purchases),
            'unique_routes': len(route_popularity),
            'active_users': total_customers,
            'avg_popularity': sum(route_popularity.values()) / len(route_popularity) if route_popularity else 0,
            'popular_routes': popular_routes,
            'daily_stats': daily_stats,
            'matched_customers': customers_data['matched_customers'],
            'unmatched_customers': customers_data['unmatched_customers'],
            'cache_info': {
                'cached': True,
                'calculation_time': calculation_time
            }
        }
        
        # Сохраняем в кэш
        _route_statistics_cache = result
        _route_statistics_cache_time = current_time
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики маршрутов: {e}")
        return {
            'total_purchases': 0,
            'unique_routes': 0,
            'active_users': 0,
            'avg_popularity': 0,
            'popular_routes': [],
            'daily_stats': [],
            'matched_customers': 0,
            'unmatched_customers': 0,
            'cache_info': {
                'cached': False,
                'calculation_time': 0,
                'error': str(e)
            }
        }


def get_route_statistics_fast(session: Session, force_refresh: bool = False) -> dict:
    """
    Быстрая версия статистики маршрутов через SQL-запросы
    """
    global _route_statistics_cache, _route_statistics_cache_time
    
    # Проверяем кэш
    current_time = time.time()
    if (not force_refresh and 
        _route_statistics_cache is not None and 
        _route_statistics_cache_time is not None and
        current_time - _route_statistics_cache_time < _route_statistics_cache_ttl):
        
        logger.info("Возвращаем статистику маршрутов из кэша")
        return _route_statistics_cache
    
    logger.info("Начинаем быстрый расчет статистики маршрутов...")
    start_time = time.time()
    
    try:
        # 1. Базовая статистика покупок
        total_purchases = session.exec(select(func.count(Purchase.id))).one()
        active_users = session.exec(select(func.count(func.distinct(Purchase.user_external_id)))).one()
        
        if total_purchases == 0:
            result = {
                'total_purchases': 0,
                'unique_routes': 0,
                'active_users': 0,
                'avg_popularity': 0,
                'popular_routes': [],
                'daily_stats': [],
                'matched_customers': 0,
                'unmatched_customers': 0,
                'cache_info': {
                    'cached': False,
                    'calculation_time': 0
                }
            }
            _route_statistics_cache = result
            _route_statistics_cache_time = current_time
            return result
        
        # 2. Получаем все покупки с группировкой по пользователям (упрощенная версия)
        all_purchases = session.exec(select(Purchase.user_external_id, Purchase.concert_id)).all()
        
        # Группируем покупки по пользователям
        user_purchases = {}
        for purchase in all_purchases:
            user_id = purchase.user_external_id
            if user_id not in user_purchases:
                user_purchases[user_id] = []
            user_purchases[user_id].append(purchase.concert_id)
        
        # 3. Получаем все маршруты
        from models import Route
        all_routes = session.exec(select(Route)).all()
        
        # 4. Быстрый подсчет популярности маршрутов
        route_popularity = {}
        route_details = {}
        matched_customers = 0
        
        for user_id, user_concert_ids in user_purchases.items():
            user_concerts = set(user_concert_ids)
            
            # Ищем точные совпадения маршрутов
            for route in all_routes:
                try:
                    route_concerts = set(int(x.strip()) for x in route.Sostav.split(',') if x.strip())
                    
                    # Точное совпадение
                    if route_concerts == user_concerts:
                        if route.id not in route_popularity:
                            route_popularity[route.id] = 0
                            route_details[route.id] = {
                                'route_id': route.id,
                                'route_name': f"Маршрут {route.id}",
                                'route_days': route.Days,
                                'route_concerts': route.Concerts,
                                'route_halls': route.Halls,
                                'route_genre': route.Genre,
                                'route_comfort_score': route.ComfortScore,
                                'route_intellect_score': route.IntellectScore
                            }
                        route_popularity[route.id] += 1
                        matched_customers += 1
                        break
                        
                except (ValueError, AttributeError):
                    continue
        
        unmatched_customers = active_users - matched_customers
        
        # 5. Сортируем маршруты по популярности
        sorted_routes = sorted(route_popularity.items(), key=lambda x: x[1], reverse=True)
        
        # 6. Подготавливаем топ маршрутов
        popular_routes = []
        for route_id, customer_count in sorted_routes[:20]:
            route_detail = route_details[route_id]
            percentage = (customer_count / active_users * 100) if active_users > 0 else 0
            
            popular_routes.append({
                'route_id': route_id,
                'route_name': route_detail['route_name'],
                'purchase_count': customer_count,
                'percentage': percentage,
                'last_purchase': None,  # Упрощено для скорости
                'status': 'available',
                'route_details': {
                    'days': route_detail['route_days'],
                    'concerts': route_detail['route_concerts'],
                    'halls': route_detail['route_halls'],
                    'genre': route_detail['route_genre'],
                    'comfort_score': route_detail['route_comfort_score'],
                    'intellect_score': route_detail['route_intellect_score']
                }
            })
        
        # 7. Упрощенная статистика по дням
        daily_stats = []
        concert_dates = session.exec(
            select(Concert.datetime)
            .distinct()
            .order_by(Concert.datetime)
        ).all()
        
        concerts_by_day = {}
        for concert_datetime in concert_dates:
            if concert_datetime:
                day_date = concert_datetime.date()
                if day_date not in concerts_by_day:
                    concerts_by_day[day_date] = []
                concerts_by_day[day_date].append(concert_datetime)
        
        for day_num, (day_date, day_concerts) in enumerate(concerts_by_day.items(), 1):
            day_concert_ids = [c.id for c in day_concerts]
            
            # Подсчитываем покупки для этого дня
            day_purchases = session.exec(
                select(func.count(Purchase.id))
                .where(Purchase.concert_id.in_(day_concert_ids))
            ).one()
            
            daily_stats.append({
                'day': day_num,
                'date': day_date,
                'purchases': day_purchases,
                'routes': 0,  # Упрощено для скорости
                'popularity': (day_purchases / total_purchases * 100) if total_purchases > 0 else 0
            })
        
        calculation_time = time.time() - start_time
        logger.info(f"Быстрая статистика маршрутов рассчитана за {calculation_time:.2f} секунд")
        
        result = {
            'total_purchases': total_purchases,
            'unique_routes': len(route_popularity),
            'active_users': active_users,
            'avg_popularity': sum(route_popularity.values()) / len(route_popularity) if route_popularity else 0,
            'popular_routes': popular_routes,
            'daily_stats': daily_stats,
            'matched_customers': matched_customers,
            'unmatched_customers': unmatched_customers,
            'cache_info': {
                'cached': True,
                'calculation_time': calculation_time
            }
        }
        
        # Сохраняем в кэш
        _route_statistics_cache = result
        _route_statistics_cache_time = current_time
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при получении быстрой статистики маршрутов: {e}")
        return {
            'total_purchases': 0,
            'unique_routes': 0,
            'active_users': 0,
            'avg_popularity': 0,
            'popular_routes': [],
            'daily_stats': [],
            'matched_customers': 0,
            'unmatched_customers': 0,
            'cache_info': {
                'cached': False,
                'calculation_time': 0,
                'error': str(e)
            }
        }


def get_route_statistics_simple(session: Session, force_refresh: bool = False) -> dict:
    """
    Простая и быстрая статистика маршрутов на основе данных из CustomerRouteMatch
    """
    global _route_statistics_cache, _route_statistics_cache_time
    
    # Проверяем кэш
    current_time = time.time()
    if (not force_refresh and 
        _route_statistics_cache is not None and 
        _route_statistics_cache_time is not None and
        current_time - _route_statistics_cache_time < _route_statistics_cache_ttl):
        
        logger.info("Возвращаем статистику маршрутов из кэша")
        return _route_statistics_cache
    
    logger.info("Начинаем простой расчет статистики маршрутов...")
    start_time = time.time()
    
    try:
        from models import CustomerRouteMatch, Route, Purchase, Concert
        
        # 1. Базовая статистика покупок
        total_purchases = session.exec(select(func.count(Purchase.id))).one()
        active_users = session.exec(select(func.count(func.distinct(Purchase.user_external_id)))).one()
        
        if total_purchases == 0:
            result = {
                'total_purchases': 0,
                'unique_routes': 0,
                'active_users': 0,
                'avg_popularity': 0,
                'popular_routes': [],
                'daily_stats': [],
                'matched_customers': 0,
                'unmatched_customers': 0,
                'cache_info': {
                    'cached': False,
                    'calculation_time': 0
                }
            }
            _route_statistics_cache = result
            _route_statistics_cache_time = current_time
            return result
        
        # 2. Получаем все соответствия маршрутов из CustomerRouteMatch
        matches = session.exec(select(CustomerRouteMatch)).all()
        
        # 3. Подсчитываем статистику
        matched_customers = 0
        unmatched_customers = 0
        route_popularity = {}
        route_details = {}
        
        for match in matches:
            if match.found and match.best_route_id:
                matched_customers += 1
                
                # Увеличиваем счетчик популярности маршрута
                if match.best_route_id not in route_popularity:
                    route_popularity[match.best_route_id] = 0
                route_popularity[match.best_route_id] += 1
            else:
                unmatched_customers += 1
        
        # 4. Получаем детали маршрутов для популярных
        if route_popularity:
            route_ids = list(route_popularity.keys())
            routes = session.exec(select(Route).where(Route.id.in_(route_ids))).all()
            
            for route in routes:
                route_details[route.id] = {
                    'route_id': route.id,
                    'route_name': f"Маршрут {route.id}",
                    'route_days': route.Days,
                    'route_concerts': route.Concerts,
                    'route_halls': route.Halls,
                    'route_genre': route.Genre,
                    'route_comfort_score': route.ComfortScore,
                    'route_intellect_score': route.IntellectScore
                }
        
        # 5. Сортируем маршруты по популярности
        sorted_routes = sorted(route_popularity.items(), key=lambda x: x[1], reverse=True)
        
        # 6. Подготавливаем топ маршрутов
        popular_routes = []
        for route_id, customer_count in sorted_routes[:20]:
            route_detail = route_details.get(route_id, {})
            percentage = (customer_count / active_users * 100) if active_users > 0 else 0
            
            popular_routes.append({
                'route_id': route_id,
                'route_name': route_detail.get('route_name', f"Маршрут {route_id}"),
                'purchase_count': customer_count,
                'percentage': percentage,
                'last_purchase': None,  # Упрощено для скорости
                'status': 'available',
                'route_details': {
                    'days': route_detail.get('route_days'),
                    'concerts': route_detail.get('route_concerts'),
                    'halls': route_detail.get('route_halls'),
                    'genre': route_detail.get('route_genre'),
                    'comfort_score': route_detail.get('route_comfort_score'),
                    'intellect_score': route_detail.get('route_intellect_score')
                }
            })
        
        # 7. Упрощенная статистика по дням
        daily_stats = []
        concert_dates = session.exec(
            select(Concert.datetime)
            .distinct()
            .order_by(Concert.datetime)
        ).all()
        
        concerts_by_day = {}
        for concert_datetime in concert_dates:
            if concert_datetime:
                day_date = concert_datetime.date()
                if day_date not in concerts_by_day:
                    concerts_by_day[day_date] = []
                concerts_by_day[day_date].append(concert_datetime)
        
        for day_num, (day_date, day_concerts) in enumerate(concerts_by_day.items(), 1):
            # Получаем ID концертов для этого дня
            day_concert_ids = session.exec(
                select(Concert.id)
                .where(Concert.datetime.in_(day_concerts))
            ).all()
            
            # Подсчитываем покупки для этого дня
            day_purchases = session.exec(
                select(func.count(Purchase.id))
                .where(Purchase.concert_id.in_(day_concert_ids))
            ).one()
            
            daily_stats.append({
                'day': day_num,
                'date': day_date,
                'purchases': day_purchases,
                'routes': 0,  # Упрощено для скорости
                'popularity': (day_purchases / total_purchases * 100) if total_purchases > 0 else 0
            })
        
        calculation_time = time.time() - start_time
        logger.info(f"Простая статистика маршрутов рассчитана за {calculation_time:.2f} секунд")
        
        result = {
            'total_purchases': total_purchases,
            'unique_routes': len(route_popularity),
            'active_users': active_users,
            'avg_popularity': sum(route_popularity.values()) / len(route_popularity) if route_popularity else 0,
            'popular_routes': popular_routes,
            'daily_stats': daily_stats,
            'matched_customers': matched_customers,
            'unmatched_customers': unmatched_customers,
            'cache_info': {
                'cached': True,
                'calculation_time': calculation_time
            }
        }
        
        # Сохраняем в кэш
        _route_statistics_cache = result
        _route_statistics_cache_time = current_time
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при получении простой статистики маршрутов: {e}")
        return {
            'total_purchases': 0,
            'unique_routes': 0,
            'active_users': 0,
            'avg_popularity': 0,
            'popular_routes': [],
            'daily_stats': [],
            'matched_customers': 0,
            'unmatched_customers': 0,
            'cache_info': {
                'cached': False,
                'calculation_time': 0,
                'error': str(e)
            }
        }


def clear_route_statistics_cache():
    """
    Очищает кэш статистики маршрутов
    """
    global _route_statistics_cache, _route_statistics_cache_time
    _route_statistics_cache = None
    _route_statistics_cache_time = None
    logger.info("Кэш статистики маршрутов очищен") 