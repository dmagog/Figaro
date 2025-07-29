"""
Утилиты для форматирования данных пользователя
"""
from datetime import datetime
from services.logging.logging import get_logger

logger = get_logger(logger_name=__name__)


def group_concerts_by_day(concerts_data: list, festival_days_data: list = None) -> dict:
    """
    Группирует концерты по дням фестиваля с учетом порядковых номеров дней
    
    Args:
        concerts_data: Список концертов пользователя
        festival_days_data: Список всех дней фестиваля
        
    Returns:
        Словарь с концертами, сгруппированными по дням, и информацией о порядковых номерах
    """
    concerts_by_day = {}
    
    logger.info(f"Starting to group {len(concerts_data)} concerts by day")
    
    # Создаем маппинг дат на порядковые номера дней фестиваля
    date_to_festival_day = {}
    if festival_days_data:
        for i, day_data in enumerate(festival_days_data, 1):
            date_to_festival_day[day_data['day']] = i
        logger.info(f"Created date mapping: {date_to_festival_day}")
    
    for i, concert in enumerate(concerts_data):
        concert_date = None
        if concert['concert'].get('datetime'):
            concert_date = concert['concert']['datetime'].date()
        
        # Определяем порядковый номер дня фестиваля
        if concert_date and concert_date in date_to_festival_day:
            festival_day_number = date_to_festival_day[concert_date]
        else:
            # Если дата не найдена в днях фестиваля, используем старую логику
            festival_day_number = concert.get('concert_day_index', 0)
        
        logger.info(f"Concert {i}: date={concert_date}, festival_day_number={festival_day_number}")
        
        if festival_day_number > 0:
            if festival_day_number not in concerts_by_day:
                concerts_by_day[festival_day_number] = []
            concerts_by_day[festival_day_number].append(concert)
            logger.info(f"Added concert to festival day {festival_day_number}")
        else:
            logger.warning(f"Concert {i} has festival_day_number=0, skipping")
    
    # Сортируем концерты в каждом дне по времени
    for day_concerts in concerts_by_day.values():
        try:
            day_concerts.sort(key=lambda x: x['concert'].get('datetime') if x['concert'].get('datetime') else datetime.min)
        except Exception as e:
            logger.warning(f"Error sorting concerts by time: {e}")
            # Если не удалось отсортировать, оставляем как есть
            pass
    
    logger.info(f"Final grouped concerts by festival day: {concerts_by_day}")
    return concerts_by_day 