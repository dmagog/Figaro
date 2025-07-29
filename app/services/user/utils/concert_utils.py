"""
Утилиты для работы с концертами пользователя
"""
from models.festival_day import FestivalDay
from sqlmodel import select
from collections import Counter
from services.logging.logging import get_logger

logger = get_logger(logger_name=__name__)


def get_all_festival_days_with_visit_status(session, concerts_data: list) -> list:
    """
    Получает все дни фестиваля с отметкой о посещении пользователем
    
    Args:
        session: Сессия базы данных
        concerts_data: Список концертов пользователя
        
    Returns:
        Список дней фестиваля с информацией о посещении
    """
    # Получаем все дни фестиваля
    all_festival_days = session.exec(select(FestivalDay).order_by(FestivalDay.day)).all()
    
    # Счетчик посещений дней пользователем
    days_counter = Counter()
    
    # Обрабатываем концерты пользователя
    for concert_data in concerts_data:
        concert = concert_data['concert']
        if concert.get('datetime'):
            concert_date = concert['datetime'].date()
            days_counter[concert_date] += 1
    
    # Формируем список всех дней фестиваля с количеством посещений
    days_with_status = []
    for festival_day in all_festival_days:
        visit_count = days_counter.get(festival_day.day, 0)
        days_with_status.append({
            "day": festival_day.day,
            "visit_count": visit_count,
            "is_visited": visit_count > 0,
            "total_concerts": festival_day.concert_count,
            "available_concerts": festival_day.available_concerts
        })
    
    return days_with_status 