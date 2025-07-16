"""
Сервис для работы с маршрутами и их доступностью
"""
from sqlmodel import Session, select, delete
from models import Route, AvailableRoute, Concert, Statistics
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
        
        if not concert_ids:
            logger.debug(f"Маршрут {route.id} не содержит концертов")
            return False
        
        # Получаем все концерты маршрута одним запросом
        concerts = session.exec(
            select(Concert).where(Concert.external_id.in_(concert_ids))
        ).all()
        
        # Проверяем, что все концерты найдены и доступны
        found_concert_ids = {c.external_id for c in concerts}
        missing_concerts = set(concert_ids) - found_concert_ids
        
        if missing_concerts:
            logger.debug(f"Концерты {missing_concerts} не найдены для маршрута {route.id}")
            return False
        
        # Проверяем доступность всех концертов
        unavailable_concerts = [c.external_id for c in concerts if not c.tickets_available]
        if unavailable_concerts:
            logger.debug(f"Концерты {unavailable_concerts} недоступны (нет билетов) для маршрута {route.id}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при проверке доступности маршрута {route.id}: {e}")
        return False


def is_route_available_optimized(session: Session, route: Route, concerts_cache: Dict[int, Concert] = None) -> bool:
    """
    Оптимизированная версия проверки доступности маршрута с использованием кэша концертов
    
    Args:
        session: Сессия базы данных
        route: Маршрут для проверки
        concerts_cache: Кэш концертов {external_id: Concert}
        
    Returns:
        bool: True если все концерты доступны, False иначе
    """
    try:
        # Парсим состав маршрута (например: "1,2,3,4")
        concert_ids = [int(x.strip()) for x in route.Sostav.split(',') if x.strip()]
        
        if not concert_ids:
            logger.debug(f"Маршрут {route.id} не содержит концертов")
            return False
        
        if concerts_cache:
            # Используем кэш концертов
            missing_concerts = []
            unavailable_concerts = []
            
            for concert_id in concert_ids:
                concert = concerts_cache.get(concert_id)
                if not concert:
                    missing_concerts.append(concert_id)
                elif not concert.tickets_available:
                    unavailable_concerts.append(concert_id)
            
            if missing_concerts:
                logger.debug(f"Концерты {missing_concerts} не найдены для маршрута {route.id}")
                return False
            
            if unavailable_concerts:
                logger.debug(f"Концерты {unavailable_concerts} недоступны (нет билетов) для маршрута {route.id}")
                return False
            
            return True
        else:
            # Если кэш не передан, используем обычную версию
            return is_route_available(session, route)
        
    except Exception as e:
        logger.error(f"Ошибка при оптимизированной проверке доступности маршрута {route.id}: {e}")
        return False


def init_available_routes(session: Session, status_dict: Dict = None) -> Dict[str, int]:
    """
    Инициализирует AvailableRoute, копируя все доступные маршруты
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Dict с статистикой: {'total_routes': int, 'available_routes': int, 'unavailable_routes': int}
    """
    try:
        logger.info("Начинаем инициализацию AvailableRoute...")
        
        # Проверяем, есть ли уже AvailableRoute
        existing_count = len(session.exec(select(AvailableRoute)).all())
        if existing_count > 0:
            logger.info(f"AvailableRoute уже существуют ({existing_count} записей), пропускаем инициализацию")
            return {
                'total_routes': len(session.exec(select(Route)).all()),
                'available_routes': existing_count,
                'unavailable_routes': 0
            }
        
        # Очищаем старые данные
        session.exec(delete(AvailableRoute))
        session.commit()
        logger.info("Удалены старые записи AvailableRoute")
        
        # Получаем все маршруты и кэшируем концерты
        all_routes = session.exec(select(Route)).all()
        total_routes = len(all_routes)
        logger.info(f"Найдено {total_routes} маршрутов для проверки")
        
        # Кэшируем все концерты для быстрого доступа
        all_concerts = session.exec(select(Concert)).all()
        concerts_by_external_id = {c.external_id: c for c in all_concerts}
        logger.info(f"Кэшировано {len(concerts_by_external_id)} концертов")
        
        available_routes = []
        unavailable_count = 0
        
        # Логируем прогресс каждые 1000 маршрутов
        for i, route in enumerate(all_routes, 1):
            if is_route_available_optimized(session, route, concerts_by_external_id):
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
                
                # Обновляем глобальный статус, если передан
                if status_dict is not None:
                    status_dict["progress"] = i
                    status_dict["available_count"] = len(available_routes)
        
        # Сохраняем доступные маршруты
        if available_routes:
            session.add_all(available_routes)
            session.commit()
        
        available_count = len(available_routes)
        
        # Обновляем кэш количества доступных маршрутов
        update_available_routes_cache(session, available_count)
        
        # Обновляем кэш количества концертов в продаже
        from services.crud.tickets import get_available_concerts_count
        available_concerts_count = get_available_concerts_count(session)
        update_available_concerts_cache(session, available_concerts_count)
        
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


def update_available_routes(session: Session, status_dict: Dict = None) -> Dict[str, int]:
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
        
        # Получаем текущие доступные маршруты и все маршруты одним запросом
        current_available = session.exec(select(AvailableRoute)).all()
        current_count = len(current_available)
        
        # Получаем все оригинальные маршруты одним запросом
        all_routes = session.exec(select(Route)).all()
        routes_by_id = {route.id: route for route in all_routes}
        
        # Кэшируем все концерты для быстрого доступа
        all_concerts = session.exec(select(Concert)).all()
        concerts_by_external_id = {c.external_id: c for c in all_concerts}
        
        # Получаем все существующие AvailableRoute одним запросом
        existing_available_route_ids = {
            ar.original_route_id for ar in current_available
        }
        
        # Проверяем каждый доступный маршрут
        routes_to_delete = []
        for available_route in current_available:
            original_route = routes_by_id.get(available_route.original_route_id)
            if not original_route or not is_route_available_optimized(session, original_route, concerts_by_external_id):
                routes_to_delete.append(available_route)
        
        # Удаляем недоступные маршруты батчем
        deleted_count = len(routes_to_delete)
        if routes_to_delete:
            # Используем bulk delete для оптимизации
            route_ids_to_delete = [route.id for route in routes_to_delete]
            session.exec(delete(AvailableRoute).where(AvailableRoute.id.in_(route_ids_to_delete)))
            logger.info(f"Удалено {deleted_count} недоступных маршрутов")
        
        # Проверяем, не стали ли доступными новые маршруты
        routes_to_add = []
        total_routes = len(all_routes)
        
        logger.info(f"Проверяем {total_routes} маршрутов на доступность...")
        
        for i, route in enumerate(all_routes, 1):
            # Проверяем, есть ли уже этот маршрут в AvailableRoute (используем кэш)
            if route.id not in existing_available_route_ids and is_route_available_optimized(session, route, concerts_by_external_id):
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
                
                # Обновляем глобальный статус, если передан
                if status_dict is not None:
                    status_dict["progress"] = i
                    # Общее количество доступных маршрутов = текущие - удалённые + новые
                    status_dict["available_count"] = current_count - deleted_count + len(routes_to_add)
        
        # Добавляем новые доступные маршруты
        added_count = 0
        if routes_to_add:
            session.add_all(routes_to_add)
            added_count = len(routes_to_add)
        
        session.commit()
        
        # Получаем финальное количество
        final_count = len(session.exec(select(AvailableRoute)).all())
        
        # Обновляем кэш количества доступных маршрутов
        update_available_routes_cache(session, final_count)
        
        # Обновляем кэш количества концертов в продаже
        available_concerts_count = len(session.exec(select(Concert).where(Concert.tickets_available == True)).all())
        update_available_concerts_cache(session, available_concerts_count)
        
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
        available_routes = get_cached_available_routes_count(session)
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


def ensure_available_routes_exist(session: Session, status_dict: Dict = None) -> bool:
    """
    Проверяет, существуют ли AvailableRoute, если нет - создаёт их
    
    Args:
        session: Сессия базы данных
        
    Returns:
        bool: True если AvailableRoute были созданы, False если уже существовали
    """
    try:
        logger.info("Проверяем наличие AvailableRoute в базе данных...")
        
        # Сначала проверяем кэш
        existing_count = get_cached_available_routes_count(session)
        
        if existing_count == 0:
            # Если кэш показывает 0, проверяем реальное количество в базе
            actual_count = len(session.exec(select(AvailableRoute)).all())
            logger.info(f"Кэш показывает 0, но в базе найдено {actual_count} AvailableRoute")
            
            if actual_count == 0:
                logger.info("AvailableRoute действительно не найдены, начинаем инициализацию...")
                result = init_available_routes(session, status_dict=status_dict)
                logger.info(f"Инициализация AvailableRoute завершена: {result['available_routes']} доступных из {result['total_routes']} маршрутов")
                return True
            else:
                # Обновляем кэш с реальным количеством
                update_available_routes_cache(session, actual_count)
                logger.info(f"Кэш обновлен: {actual_count} AvailableRoute")
                return False
        else:
            logger.info(f"Найдено {existing_count} AvailableRoute в кэше, инициализация не требуется")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке AvailableRoute: {e}")
        raise


def update_available_routes_cache(session: Session, available_count: int):
    """
    Обновляет кэшированное количество доступных маршрутов в таблице Statistics
    
    Args:
        session: Сессия базы данных
        available_count: Количество доступных маршрутов
    """
    try:
        # Ищем существующую запись или создаём новую
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_routes_count")
        ).first()
        
        if stats_record:
            stats_record.value = available_count
            stats_record.updated_at = datetime.now(timezone.utc)
        else:
            stats_record = Statistics(
                key="available_routes_count",
                value=available_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
        
        session.commit()
        logger.info(f"Кэш количества доступных маршрутов обновлён: {available_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении кэша доступных маршрутов: {e}")
        session.rollback()


def get_cached_available_routes_count(session: Session) -> int:
    """
    Возвращает кэшированное количество доступных маршрутов
    
    Args:
        session: Сессия базы данных
        
    Returns:
        int: Количество доступных маршрутов из кэша
    """
    try:
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_routes_count")
        ).first()
        
        if stats_record:
            return stats_record.value
        else:
            # Если кэша нет, подсчитываем и создаём
            available_count = len(session.exec(select(AvailableRoute)).all())
            update_available_routes_cache(session, available_count)
            return available_count
            
    except Exception as e:
        logger.error(f"Ошибка при получении кэшированного количества доступных маршрутов: {e}")
        # В случае ошибки возвращаем 0
        return 0


def init_available_routes_cache(session: Session):
    """
    Инициализирует кэш количества доступных маршрутов, если его нет
    """
    try:
        # Проверяем, есть ли уже запись в кэше
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_routes_count")
        ).first()
        
        if not stats_record:
            # Если кэша нет, создаём его
            available_count = len(session.exec(select(AvailableRoute)).all())
            update_available_routes_cache(session, available_count)
            logger.info("Кэш количества доступных маршрутов инициализирован")
        else:
            logger.info("Кэш количества доступных маршрутов уже существует")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации кэша доступных маршрутов: {e}")
        session.rollback()


def update_available_concerts_cache(session: Session, available_count: int):
    """
    Обновляет кэшированное количество концертов в продаже в таблице Statistics
    
    Args:
        session: Сессия базы данных
        available_count: Количество концертов в продаже
    """
    try:
        # Ищем существующую запись или создаём новую
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_concerts_count")
        ).first()
        
        if stats_record:
            stats_record.value = available_count
            stats_record.updated_at = datetime.now(timezone.utc)
        else:
            stats_record = Statistics(
                key="available_concerts_count",
                value=available_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
        
        session.commit()
        logger.info(f"Кэш количества концертов в продаже обновлён: {available_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении кэша концертов в продаже: {e}")
        session.rollback()


def get_cached_available_concerts_count(session: Session) -> int:
    """
    Возвращает кэшированное количество концертов в продаже
    
    Args:
        session: Сессия базы данных
        
    Returns:
        int: Количество концертов в продаже из кэша
    """
    try:
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_concerts_count")
        ).first()
        
        if stats_record:
            return stats_record.value
        else:
            # Если кэша нет, подсчитываем и создаём
            available_count = len(session.exec(select(Concert).where(Concert.tickets_available == True)).all())
            update_available_concerts_cache(session, available_count)
            return available_count
            
    except Exception as e:
        logger.error(f"Ошибка при получении кэшированного количества концертов в продаже: {e}")
        # В случае ошибки возвращаем 0
        return 0


def init_available_concerts_cache(session: Session):
    """
    Инициализирует кэш количества концертов в продаже, если его нет
    """
    try:
        # Проверяем, есть ли уже запись в кэше
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "available_concerts_count")
        ).first()
        
        if not stats_record:
            # Если кэша нет, создаём его
            available_count = len(session.exec(select(Concert).where(Concert.tickets_available == True)).all())
            update_available_concerts_cache(session, available_count)
            logger.info("Кэш количества концертов в продаже инициализирован")
        else:
            logger.info("Кэш количества концертов в продаже уже существует")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации кэша концертов в продаже: {e}")
        session.rollback()


def analyze_route_performance(session: Session) -> Dict[str, any]:
    """
    Анализирует производительность системы маршрутов
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Dict с метриками производительности
    """
    try:
        from time import time
        
        # Подсчитываем общую статистику
        total_routes = len(session.exec(select(Route)).all())
        total_concerts = len(session.exec(select(Concert)).all())
        available_routes = len(session.exec(select(AvailableRoute)).all())
        
        # Анализируем распределение концертов в маршрутах
        route_lengths = []
        for route in session.exec(select(Route)).all():
            if route.Sostav:
                concert_count = len([x.strip() for x in route.Sostav.split(',') if x.strip()])
                route_lengths.append(concert_count)
        
        avg_route_length = sum(route_lengths) / len(route_lengths) if route_lengths else 0
        max_route_length = max(route_lengths) if route_lengths else 0
        min_route_length = min(route_lengths) if route_lengths else 0
        
        # Анализируем доступность концертов
        available_concerts = len(session.exec(select(Concert).where(Concert.tickets_available == True)).all())
        availability_percentage = (available_concerts / total_concerts * 100) if total_concerts > 0 else 0
        
        # Тестируем производительность проверки доступности
        test_routes = session.exec(select(Route).limit(100)).all()
        
        # Тест без кэша
        start_time = time()
        for route in test_routes[:10]:  # Тестируем только первые 10
            is_route_available(session, route)
        time_without_cache = time() - start_time
        
        # Тест с кэшем
        all_concerts = session.exec(select(Concert)).all()
        concerts_cache = {c.external_id: c for c in all_concerts}
        
        start_time = time()
        for route in test_routes[:10]:  # Тестируем только первые 10
            is_route_available_optimized(session, route, concerts_cache)
        time_with_cache = time() - start_time
        
        performance_improvement = ((time_without_cache - time_with_cache) / time_without_cache * 100) if time_without_cache > 0 else 0
        
        return {
            'total_routes': total_routes,
            'total_concerts': total_concerts,
            'available_routes': available_routes,
            'available_concerts': available_concerts,
            'availability_percentage': round(availability_percentage, 2),
            'avg_route_length': round(avg_route_length, 2),
            'max_route_length': max_route_length,
            'min_route_length': min_route_length,
            'time_without_cache_ms': round(time_without_cache * 1000, 2),
            'time_with_cache_ms': round(time_with_cache * 1000, 2),
            'performance_improvement_percent': round(performance_improvement, 2),
            'estimated_full_check_time_minutes': round((total_routes * time_with_cache / 60), 2)
        }
        
    except Exception as e:
        logger.error(f"Ошибка при анализе производительности: {e}")
        return {
            'error': str(e)
        } 