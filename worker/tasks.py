from .celery_worker import celery_app
import os
from dotenv import load_dotenv
import asyncio
from bot.utils import send_telegram_message as tg_send
from celery.utils.log import get_task_logger
from datetime import datetime
import sys

# Добавляем путь к app для импорта моделей
sys.path.append("/app")

load_dotenv()
logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_telegram_message(self, telegram_id: int, text: str = None, file_path: str = None, file_type: str = None, parse_mode: str = None, message_id: int = None):
    logger.info(f"[Celery] Отправка сообщения пользователю {telegram_id}: {text} (file: {file_path}, type: {file_type}, parse_mode: {parse_mode}, message_id: {message_id})")
    
    # Обновляем статус сообщения в базе данных
    if message_id:
        try:
            from sqlmodel import Session, select
            from app.models import TelegramMessage, MessageStatus
            from app.database.simple_engine import simple_engine
            
            with Session(simple_engine) as session:
                message = session.get(TelegramMessage, message_id)
                if message:
                    message.status = MessageStatus.SENT
                    message.sent_at = datetime.utcnow()
                    session.add(message)
                    session.commit()
        except Exception as e:
            logger.error(f"[Celery] Ошибка обновления статуса сообщения {message_id}: {e}")
    
    try:
        result = asyncio.run(tg_send(telegram_id, text, file_path, file_type, parse_mode))
        
        # Обновляем статус на доставлено
        if message_id and result:
            try:
                from sqlmodel import Session
                from app.models import TelegramMessage, MessageStatus
                from app.database.simple_engine import simple_engine
                
                with Session(simple_engine) as session:
                    message = session.get(TelegramMessage, message_id)
                    if message:
                        message.status = MessageStatus.DELIVERED
                        message.delivered_at = datetime.utcnow()
                        session.add(message)
                        session.commit()
            except Exception as e:
                logger.error(f"[Celery] Ошибка обновления статуса доставки {message_id}: {e}")
        
        return result
    except Exception as e:
        logger.error(f"[Celery] Ошибка отправки сообщения: {e}")
        
        # Обновляем статус на ошибку
        if message_id:
            try:
                from sqlmodel import Session
                from app.models import TelegramMessage, MessageStatus
                from app.database.simple_engine import simple_engine
                
                with Session(simple_engine) as session:
                    message = session.get(TelegramMessage, message_id)
                    if message:
                        message.status = MessageStatus.FAILED
                        message.error_message = str(e)
                        session.add(message)
                        session.commit()
            except Exception as db_error:
                logger.error(f"[Celery] Ошибка обновления статуса ошибки {message_id}: {db_error}")
        
        # Retry при ошибке 429 или любой Exception
        if hasattr(e, 'response') and getattr(e.response, 'status', None) == 429:
            logger.warning("429 Too Many Requests: повторная попытка...")
            raise self.retry(exc=e, countdown=30)
        raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def get_user_route_data_task(self, user_external_id: str):
    """Получает данные маршрута пользователя через Celery"""
    logger.info(f"[Celery] Получение данных маршрута для пользователя {user_external_id}")
    
    try:
        from app.services.crud.purchase import get_user_unique_concerts_with_details
        from app.routes.user.temp_routes import calculate_transition_time, calculate_route_statistics
        from sqlmodel import Session
        from app.database.simple_engine import simple_engine
        
        with Session(simple_engine) as session:
            # Получаем концерты пользователя
            concerts_data = get_user_unique_concerts_with_details(session, user_external_id)
            
            if not concerts_data:
                return {"error": "У вас нет концертов в маршруте"}
            
            # Сортируем концерты по времени
            sorted_concerts = sorted(concerts_data, key=lambda x: x['concert'].get('datetime', datetime.min))
            
            # Создаем структуру для статистики
            concerts_by_day_with_transitions = {}
            current_day = None
            day_concerts = []
            
            for i, concert_data in enumerate(sorted_concerts):
                concert = concert_data['concert']
                if concert.get('datetime'):
                    day = concert['datetime'].date()
                    if current_day != day:
                        if current_day and day_concerts:
                            concerts_by_day_with_transitions[current_day] = day_concerts
                        current_day = day
                        day_concerts = []
                    
                    # Добавляем информацию о переходе
                    concert_with_transition = concert_data.copy()
                    if i < len(sorted_concerts) - 1:
                        next_concert_data = sorted_concerts[i + 1]
                        transition_info = calculate_transition_time(session, concert_data, next_concert_data)
                        concert_with_transition['transition_info'] = transition_info
                    else:
                        concert_with_transition['transition_info'] = None
                    
                    day_concerts.append(concert_with_transition)
            
            # Добавляем последний день
            if current_day and day_concerts:
                concerts_by_day_with_transitions[current_day] = day_concerts
            
            # Получаем статистику
            route_stats = calculate_route_statistics(session, sorted_concerts, concerts_by_day_with_transitions)
            
            return {
                "sorted_concerts": sorted_concerts,
                "route_summary": route_stats,
                "concerts_by_day": concerts_by_day_with_transitions
            }
            
    except Exception as e:
        logger.error(f"[Celery] Ошибка при получении данных маршрута: {e}")
        import traceback
        traceback.print_exc()
        raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def format_route_concerts_list_task(self, concerts_data: dict, detailed: bool = False, day_number: int = None):
    """Форматирует список концертов для отображения через Celery"""
    logger.info(f"[Celery] Форматирование маршрута (detailed: {detailed}, day: {day_number})")
    
    try:
        sorted_concerts = concerts_data.get("sorted_concerts", [])
        if not sorted_concerts:
            return "Маршрут не найден или пуст"
        
        # Группируем концерты по дням
        concerts_by_day = {}
        for i, concert_data in enumerate(sorted_concerts):
            concert = concert_data['concert']
            if concert.get('datetime'):
                day = concert['datetime'].date()
                if day not in concerts_by_day:
                    concerts_by_day[day] = []
                concerts_by_day[day].append({
                    'index': i + 1,
                    'time': concert['datetime'].strftime("%H:%M"),
                    'name': concert.get('name', 'Название не указано'),
                    'hall': concert.get('hall', {}).get('name', 'Зал не указан'),
                    'duration': str(concert.get('duration', 'Длительность не указана')),
                    'genre': concert.get('genre', 'Жанр не указан'),
                    'concert_data': concert_data
                })
        
        # Сортируем дни
        sorted_days = sorted(concerts_by_day.keys())
        
        if day_number:
            # Показываем только конкретный день
            try:
                day_index = int(day_number) - 1
                if 0 <= day_index < len(sorted_days):
                    target_day = sorted_days[day_index]
                    day_concerts = concerts_by_day[target_day]
                    
                    # Форматируем дату
                    day_str = str(target_day.day)
                    month_names = {
                        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                        5: "мая", 6: "июня", 7: "июля", 8: "августа",
                        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                    }
                    month_str = month_names.get(target_day.month, "месяца")
                    
                    concerts_text = f"🎈 *День {day_index + 1}* ({day_str} {month_str})\n\n"
                    
                    for concert in day_concerts:
                        if detailed:
                            concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                            concerts_text += f"   🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                            
                            if concert['concert_data'].get('transition_info'):
                                transition = concert['concert_data']['transition_info']
                                if transition.get('status') == 'success':
                                    concerts_text += f"   🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                                elif transition.get('status') == 'same_hall':
                                    concerts_text += f"   📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                            
                            concerts_text += "\n"
                        else:
                            concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
                    
                    return concerts_text
                else:
                    return f"День {day_number} не найден в маршруте"
            except ValueError:
                return f"Неверный номер дня: {day_number}"
        
        # Показываем все дни
        concerts_text = ""
        for day_index, target_day in enumerate(sorted_days, 1):
            day_concerts = concerts_by_day[target_day]
            
            # Форматируем дату
            day_str = str(target_day.day)
            month_names = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            month_str = month_names.get(target_day.month, "месяца")
            
            concerts_text += f"🎈 *День {day_index}* ({day_str} {month_str})\n\n"
            
            for concert in day_concerts:
                if detailed:
                    concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                    concerts_text += f"   🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                    
                    if concert['concert_data'].get('transition_info'):
                        transition = concert['concert_data']['transition_info']
                        if transition.get('status') == 'success':
                            concerts_text += f"   🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                        elif transition.get('status') == 'same_hall':
                            concerts_text += f"   📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                    
                    concerts_text += "\n"
                else:
                    concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
            
            concerts_text += "\n"
        
        return concerts_text.strip()
        
    except Exception as e:
        logger.error(f"[Celery] Ошибка при форматировании маршрута: {e}")
        raise self.retry(exc=e)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def format_route_summary_task(self, concerts_data: dict):
    """Форматирует статистику маршрута через Celery"""
    logger.info(f"[Celery] Форматирование статистики маршрута")
    
    try:
        route_summary = concerts_data.get("route_summary", {})
        if not route_summary:
            return "Статистика маршрута недоступна"
        
        summary_text = "📊 *Итоговая статистика маршрута:*\n\n"
        
        # Основные показатели
        summary_text += f"🎵 *Концертов:* {route_summary.get('total_concerts', 0)}\n"
        summary_text += f"📅 *Дней:* {route_summary.get('total_days', 0)}\n"
        summary_text += f"🏛️ *Залов:* {route_summary.get('total_halls', 0)}\n"
        summary_text += f"🎨 *Жанров:* {route_summary.get('total_genres', 0)}\n"
        
        # Время
        concert_time = route_summary.get('total_concert_time_minutes', 0)
        if concert_time:
            summary_text += f"⏱️ *Время концертов:* {concert_time} мин\n"
        
        trans_time = route_summary.get('total_walk_time_minutes', 0)
        if trans_time:
            summary_text += f"🚶 *Время переходов:* {trans_time} мин\n"
        
        # Расстояние
        distance = route_summary.get('total_distance_km', 0)
        if distance:
            summary_text += f"📍 *Пройдено:* {distance} км\n"
        
        # Контент
        compositions = route_summary.get('unique_compositions', 0)
        if compositions:
            summary_text += f"🎼 *Произведений:* {compositions}\n"
        
        authors = route_summary.get('unique_authors', 0)
        if authors:
            summary_text += f"✍️ *Авторов:* {authors}\n"
        
        artists = route_summary.get('unique_artists', 0)
        if artists:
            summary_text += f"🎭 *Артистов:* {artists}\n"
        
        summary_text += "\n🎉 *Спасибо, что выбрали наш фестиваль! До встречи на концертах!*"
        
        return summary_text
        
    except Exception as e:
        logger.error(f"[Celery] Ошибка при форматировании статистики: {e}")
        raise self.retry(exc=e) 