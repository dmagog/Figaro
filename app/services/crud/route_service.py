"""
Сервис для работы с маршрутами и их доступностью
"""
from sqlmodel import Session, select, delete
from models import Route, AvailableRoute, Concert
from datetime import datetime, timezone
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


def is_route_available(session: Session, route: Route) -> bool:
    """
    Проверяет, доступны ли все концерты в маршруте
    
    Args:
        session: Сессия базы данных
        route: Маршрут для проверки
        
    Returns:
        bool: True если все концерты доступны, False иначе
    """
    try:
        # Парсим состав маршрута (например: "1,2,3,4")
        concert_ids = [int(x.strip()) for x in route.Sostav.split(',') if x.strip()]
        
        # Проверяем доступность каждого концерта
        for concert_id in concert_ids:
            concert = session.exec(
                select(Concert).where(Concert.external_id == concert_id)
            ).first()
            
            if not concert:
                logger.debug(f"Концерт {concert_id} не найден для маршрута {route.id}")
                return False
            elif not concert.tickets_available:
                logger.debug(f"Концерт {concert_id} недоступен (нет билетов) для маршрута {route.id}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности маршрута {route.id}: {e}")
        return False


def init_available_routes(session: Session) -> Dict[str, int]:
    """
    Инициализирует AvailableRoute, копируя все доступные маршруты
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Dict с статистикой: {'total_routes': int, 'available_routes': int, 'unavailable_routes': int}
    """
    try:
        logger.info("Начинаем инициализацию AvailableRoute...")
        
        # Очищаем старые данные
        session.exec(delete(AvailableRoute))
        session.commit()
        logger.info("Удалены старые записи AvailableRoute")
        
        # Получаем все маршруты
        all_routes = session.exec(select(Route)).all()
        total_routes = len(all_routes)
        logger.info(f"Найдено {total_routes} маршрутов для проверки")
        
        available_routes = []
        unavailable_count = 0
        
        # Логируем прогресс каждые 1000 маршрутов
        for i, route in enumerate(all_routes, 1):
            if is_route_available(session, route):
                # Создаём копию маршрута для AvailableRoute
                available_route_data = route.model_dump()
                available_route_data['original_route_id'] = route.id
                available_route_data['last_availability_check'] = datetime.now(timezone.utc)
                
                available_route = AvailableRoute(**available_route_data)
                available_routes.append(available_route)
            else:
                unavailable_count += 1
            
            # Логируем прогресс каждые 1000 маршрутов
            if i % 1000 == 0 or i == total_routes:
                percent = (i / total_routes) * 100 if total_routes > 0 else 100
                logger.info(f"Проверено {i}/{total_routes} маршрутов ({percent:.1f}%) - найдено доступных: {len(available_routes)}")
        
        # Сохраняем доступные маршруты
        if available_routes:
            session.add_all(available_routes)
            session.commit()
        
        available_count = len(available_routes)
        
        logger.info(f"Инициализация завершена: {available_count} доступных, {unavailable_count} недоступных из {total_routes} маршрутов")
        
        return {
            'total_routes': total_routes,
            'available_routes': available_count,
            'unavailable_routes': unavailable_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации AvailableRoute: {e}")
        session.rollback()
        raise


def update_available_routes(session: Session) -> Dict[str, int]:
    """
    Обновляет AvailableRoute, удаляя маршруты с недоступными концертами
    и добавляя маршруты, которые снова стали доступными
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Dict с статистикой изменений
    """
    try:
        logger.info("Начинаем обновление AvailableRoute...")
        
        # Получаем текущие доступные маршруты
        current_available = session.exec(select(AvailableRoute)).all()
        current_count = len(current_available)
        
        # Проверяем каждый доступный маршрут
        routes_to_delete = []
        for available_route in current_available:
            # Получаем оригинальный маршрут для проверки
            original_route = session.exec(
                select(Route).where(Route.id == available_route.original_route_id)
            ).first()
            
            if not original_route or not is_route_available(session, original_route):
                routes_to_delete.append(available_route)
        
        # Удаляем недоступные маршруты
        deleted_count = 0
        for route in routes_to_delete:
            session.delete(route)
            deleted_count += 1
        
        # Проверяем, не стали ли доступными новые маршруты
        all_routes = session.exec(select(Route)).all()
        routes_to_add = []
        total_routes = len(all_routes)
        
        logger.info(f"Проверяем {total_routes} маршрутов на доступность...")
        
        for i, route in enumerate(all_routes, 1):
            # Проверяем, есть ли уже этот маршрут в AvailableRoute
            existing = session.exec(
                select(AvailableRoute).where(AvailableRoute.original_route_id == route.id)
            ).first()
            
            if not existing and is_route_available(session, route):
                # Создаём новую запись AvailableRoute
                available_route_data = route.model_dump()
                available_route_data['original_route_id'] = route.id
                available_route_data['last_availability_check'] = datetime.now(timezone.utc)
                
                available_route = AvailableRoute(**available_route_data)
                routes_to_add.append(available_route)
            
            # Логируем прогресс каждые 1000 маршрутов
            if i % 1000 == 0 or i == total_routes:
                percent = (i / total_routes) * 100 if total_routes > 0 else 100
                logger.info(f"Проверено {i}/{total_routes} маршрутов ({percent:.1f}%) - найдено новых доступных: {len(routes_to_add)}")
        
        # Добавляем новые доступные маршруты
        added_count = 0
        if routes_to_add:
            session.add_all(routes_to_add)
            added_count = len(routes_to_add)
        
        session.commit()
        
        # Получаем финальное количество
        final_count = len(session.exec(select(AvailableRoute)).all())
        
        logger.info(f"Обновление завершено: удалено {deleted_count}, добавлено {added_count}, всего доступно {final_count}")
        
        return {
            'previous_count': current_count,
            'deleted_count': deleted_count,
            'added_count': added_count,
            'current_count': final_count,
            'net_change': final_count - current_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении AvailableRoute: {e}")
        session.rollback()
        raise


def get_available_routes_stats(session: Session) -> Dict[str, int]:
    """
    Получает статистику по доступным маршрутам
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Dict с статистикой
    """
    try:
        total_routes = len(session.exec(select(Route)).all())
        available_routes = len(session.exec(select(AvailableRoute)).all())
        unavailable_routes = total_routes - available_routes
        
        return {
            'total_routes': total_routes,
            'available_routes': available_routes,
            'unavailable_routes': unavailable_routes,
            'availability_percentage': round((available_routes / total_routes * 100), 2) if total_routes > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики маршрутов: {e}")
        return {
            'total_routes': 0,
            'available_routes': 0,
            'unavailable_routes': 0,
            'availability_percentage': 0
        }


def ensure_available_routes_exist(session: Session) -> bool:
    """
    Проверяет, существуют ли AvailableRoute, если нет - создаёт их
    
    Args:
        session: Сессия базы данных
        
    Returns:
        bool: True если AvailableRoute были созданы, False если уже существовали
    """
    try:
        logger.info("Проверяем наличие AvailableRoute в базе данных...")
        existing_count = len(session.exec(select(AvailableRoute)).all())
        
        if existing_count == 0:
            logger.info("AvailableRoute не найдены, начинаем инициализацию...")
            result = init_available_routes(session)
            logger.info(f"Инициализация AvailableRoute завершена: {result['available_routes']} доступных из {result['total_routes']} маршрутов")
            return True
        else:
            logger.info(f"Найдено {existing_count} AvailableRoute, инициализация не требуется")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке AvailableRoute: {e}")
        raise 