"""
Сервис для работы с билетами и внешним API продажи
"""
from sqlmodel import Session, select
from models import Concert
from typing import Dict, List, Optional, Tuple
import logging
import asyncio
from datetime import datetime, timezone
import random

logger = logging.getLogger(__name__)


class TicketsService:
    """Сервис для работы с билетами"""
    
    def __init__(self):
        # Кэш для хранения информации о билетах
        self._cache = {}
        self._cache_ttl = 300  # 5 минут в секундах
        # Счётчик запросов для создания эффекта изменения данных
        self._request_counter = 0
    
    def get_tickets_left(self, concert_id: int) -> int:
        """
        Получает количество оставшихся билетов для концерта
        Временная заглушка, которая будет заменена на реальный API
        
        Args:
            concert_id: ID концерта
            
        Returns:
            int: Количество оставшихся билетов
        """
        # Проверяем кэш
        cache_key = f"tickets_{concert_id}"
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if (datetime.now(timezone.utc) - timestamp).seconds < self._cache_ttl:
                return cached_data
        
        # В реальной системе здесь был бы HTTP запрос к внешнему API
        # Сейчас возвращаем значение из базы данных или генерируем случайное
        from sqlmodel import Session, select
        from models import Concert
        from database.database import get_session
        
        # Получаем концерт из базы
        with next(get_session()) as session:
            concert = session.exec(select(Concert).where(Concert.id == concert_id)).first()
            if concert and concert.tickets_left is not None:
                tickets_left = concert.tickets_left
            else:
                # Если данных нет, генерируем случайное значение
                tickets_left = random.randint(0, 50)
        
        # Сохраняем в кэш
        self._cache[cache_key] = (tickets_left, datetime.now(timezone.utc))
        
        return tickets_left
    
    def get_concerts_availability(self, session: Session, concert_ids: Optional[List[int]] = None) -> Dict[int, Dict]:
        """
        Получает информацию о доступности билетов для концертов
        
        Args:
            session: Сессия базы данных
            concert_ids: Список ID концертов (если None, то для всех концертов)
            
        Returns:
            Dict[int, Dict]: Словарь с информацией о билетах
        """
        try:
            # Увеличиваем счётчик запросов
            self._request_counter += 1
            
            # Получаем концерты
            if concert_ids:
                concerts = session.exec(
                    select(Concert).where(Concert.id.in_(concert_ids))
                ).all()
            else:
                concerts = session.exec(select(Concert)).all()
            
            result = {}
            
            # Определяем общее количество концертов
            total_concerts = len(concerts)
            
            # Проверяем, сколько концертов уже недоступны
            currently_unavailable = sum(1 for c in concerts if not c.tickets_available or (c.tickets_left is not None and c.tickets_left == 0))
            currently_available = total_concerts - currently_unavailable
            
            # Если все концерты недоступны, восстанавливаем их до максимальной вместимости
            if currently_unavailable >= total_concerts:
                logger.info(f"Все концерты недоступны! Восстанавливаем {total_concerts} концертов до максимальной вместимости")
                
                for concert in concerts:
                    hall = concert.hall
                    max_seats = hall.seats if hall else 100
                    concert.tickets_left = max_seats
                    concert.tickets_available = True
                    session.add(concert)
                
                session.commit()
                logger.info(f"Все {total_concerts} концертов восстановлены и доступны для продажи")
            
            # Определяем, сколько концертов сделать недоступными (20-40% от общего количества)
            unavailable_count = max(1, int(total_concerts * random.uniform(0.2, 0.4)))
            
            # Выбираем случайные концерты для "закрытия"
            concerts_to_close = random.sample(concerts, min(unavailable_count, total_concerts))
            concerts_to_close_ids = {c.id for c in concerts_to_close}
            
            # Для большей части концертов имитируем продажу билетов (уменьшаем tickets_left)
            sell_count = max(1, int(total_concerts * random.uniform(0.6, 0.9)))
            concerts_to_sell = random.sample([c for c in concerts if c.id not in concerts_to_close_ids], min(sell_count, total_concerts - len(concerts_to_close_ids)))
            concerts_to_sell_ids = {c.id for c in concerts_to_sell}
            
            logger.info(f"Запрос #{self._request_counter}: Делаем {len(concerts_to_close)} концертов недоступными, продаём билеты ещё у {len(concerts_to_sell)}")
            
            updated = False
            for concert in concerts:
                # Если концерт в списке для "закрытия", делаем его недоступным
                if concert.id in concerts_to_close_ids:
                    tickets_left = 0
                    available = False
                else:
                    # Имитация продажи билетов
                    tickets_left = concert.tickets_left if concert.tickets_left is not None else (concert.hall.seats if concert.hall else 100)
                    if concert.id in concerts_to_sell_ids and tickets_left > 0:
                        # Уменьшаем на 5-30% от текущего количества
                        sold = max(1, int(tickets_left * random.uniform(0.05, 0.3)))
                        tickets_left = max(0, tickets_left - sold)
                    available = tickets_left > 0
                
                # Получаем информацию о зале для подсчёта общего количества мест
                hall = concert.hall
                total_seats = hall.seats if hall else 100  # Заглушка
                
                # --- Обновляем поля tickets_available и tickets_left в базе, если они отличаются ---
                if concert.tickets_available != available or concert.tickets_left != tickets_left:
                    concert.tickets_available = available
                    concert.tickets_left = tickets_left
                    session.add(concert)
                    updated = True
                
                result[concert.id] = {
                    "concert_id": concert.id,
                    "concert_name": concert.name,
                    "available": available,
                    "tickets_left": tickets_left,
                    "total_seats": total_seats,
                    "availability_percent": round((tickets_left / total_seats * 100), 1) if total_seats > 0 else 0,
                    "last_updated": datetime.now(timezone.utc)
                }
            
            # Если были изменения, коммитим сессию
            if updated:
                session.commit()
            
            logger.info(f"Получена информация о билетах для {len(result)} концертов (доступно: {sum(1 for r in result.values() if r['available'])})")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о билетах: {e}")
            return {}
    
    def get_concert_availability(self, session: Session, concert_id: int) -> Optional[Dict]:
        """
        Получает информацию о доступности билетов для конкретного концерта
        
        Args:
            session: Сессия базы данных
            concert_id: ID концерта
            
        Returns:
            Optional[Dict]: Информация о билетах или None
        """
        try:
            concert = session.exec(select(Concert).where(Concert.id == concert_id)).first()
            if not concert:
                logger.warning(f"Концерт с ID {concert_id} не найден")
                return None
            
            tickets_left = self.get_tickets_left(concert_id)
            hall = concert.hall
            total_seats = hall.seats if hall else 100
            
            return {
                "concert_id": concert.id,
                "concert_name": concert.name,
                "available": tickets_left > 0,
                "tickets_left": tickets_left,
                "total_seats": total_seats,
                "availability_percent": round((tickets_left / total_seats * 100), 1) if total_seats > 0 else 0,
                "last_updated": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о билетах для концерта {concert_id}: {e}")
            return None
    
    def get_available_concerts_count(self, session: Session) -> int:
        """
        Получает количество концертов с доступными билетами
        
        Args:
            session: Сессия базы данных
            
        Returns:
            int: Количество концертов с доступными билетами
        """
        try:
            concerts = session.exec(select(Concert)).all()
            available_count = 0
            
            for concert in concerts:
                tickets_left = self.get_tickets_left(concert.id)
                if tickets_left > 0:
                    available_count += 1
            
            return available_count
            
        except Exception as e:
            logger.error(f"Ошибка при подсчёте доступных концертов: {e}")
            return 0
    
    def clear_cache(self):
        """Очищает кэш билетов"""
        self._cache.clear()
        logger.info("Кэш билетов очищен")
    
    def get_cache_stats(self) -> Dict:
        """Получает статистику кэша"""
        return {
            "cache_size": len(self._cache),
            "cache_ttl": self._cache_ttl,
            "cached_items": list(self._cache.keys()),
            "request_counter": self._request_counter
        }


# Глобальный экземпляр сервиса
tickets_service = TicketsService()


# Функции для обратной совместимости
def get_tickets_left(concert_id: int) -> int:
    """
    Функция для обратной совместимости с существующим кодом
    
    Args:
        concert_id: ID концерта
        
    Returns:
        int: Количество оставшихся билетов
    """
    return tickets_service.get_tickets_left(concert_id)


def get_concerts_availability(session: Session, concert_ids: Optional[List[int]] = None) -> Dict[int, Dict]:
    """
    Функция для обратной совместимости с существующим кодом
    
    Args:
        session: Сессия базы данных
        concert_ids: Список ID концертов
        
    Returns:
        Dict[int, Dict]: Словарь с информацией о билетах
    """
    return tickets_service.get_concerts_availability(session, concert_ids)


def get_available_concerts_count(session: Session) -> int:
    """
    Функция для обратной совместимости с существующим кодом
    
    Args:
        session: Сессия базы данных
        
    Returns:
        int: Количество концертов с доступными билетами
    """
    return tickets_service.get_available_concerts_count(session) 