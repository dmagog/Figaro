from sqlmodel import Session, select
from models import User, MessageTemplate
from app.services.telegram_service import TelegramService
from worker.tasks import send_telegram_message
import logging

logger = logging.getLogger(__name__)

class BotApiService:
    """Сервис для обработки API запросов от Telegram бота"""
    
    @staticmethod
    def send_template_message(telegram_id: int, template_id: int, session: Session):
        """Отправляет персонализированное сообщение по шаблону через Celery"""
        try:
            # Получаем пользователя
            user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
            if not user:
                return {"error": "Пользователь не найден", "code": 404}
            
            # Получаем шаблон
            template = session.get(MessageTemplate, template_id)
            if not template:
                return {"error": "Шаблон не найден", "code": 404}
            
            # Персонализируем сообщение
            user_data = TelegramService.get_user_data(user, session)
            personalized_message = TelegramService.personalize_message(template.content, user_data)
            
            # Ставим задачу в очередь Celery
            task = send_telegram_message.delay(
                telegram_id, 
                personalized_message, 
                None,  # file_path
                None,  # file_type
                "Markdown"
            )
            
            logger.info(f"Bot API: Task queued {task.id} for user {telegram_id}")
            
            return {
                "success": True, 
                "task_id": task.id,
                "message": "Сообщение поставлено в очередь"
            }
            
        except Exception as e:
            logger.error(f"Bot API Error: {e}", exc_info=True)
            return {"error": f"Ошибка сервера: {str(e)}", "code": 500}
    
    @staticmethod
    def get_route_data(telegram_id: int, session: Session):
        """Получает данные маршрута пользователя"""
        try:
            # Получаем пользователя
            user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
            if not user:
                return {"error": "Пользователь не найден", "code": 404}
            
            # Получаем данные маршрута через TelegramService
            user_data = TelegramService.get_user_data(user, session)
            
            return {
                "success": True,
                "route_data": {
                    "sorted_concerts": user_data.get("sorted_concerts", []),
                    "route_summary": user_data.get("route_summary", {}),
                    "route_concerts": user_data.get("route_concerts", [])
                },
                "user_name": user.name or user.email.split('@')[0] if user.email else "Пользователь"
            }
            
        except Exception as e:
            logger.error(f"Bot API Route Error: {e}", exc_info=True)
            return {"error": f"Ошибка при получении маршрута: {str(e)}", "code": 500}
    
    @staticmethod
    def get_route_day(telegram_id: int, day_number: int, session: Session):
        """Получает маршрут на конкретный день"""
        try:
            # Получаем пользователя
            user = session.exec(select(User).where(User.telegram_id == telegram_id)).first()
            if not user:
                return {"error": "Пользователь не найден", "code": 404}
            
            # Получаем данные маршрута
            user_data = TelegramService.get_user_data(user, session)
            route_data = {
                "sorted_concerts": user_data.get("sorted_concerts", []),
                "route_summary": user_data.get("route_summary", {}),
                "route_concerts": user_data.get("route_concerts", [])
            }
            
            logger.info(f"Route data for day {day_number}: {len(route_data.get('sorted_concerts', []))} concerts")
            
            # Форматируем маршрут на конкретный день
            # Используем простую логику форматирования здесь
            formatted_route = BotApiService._format_route_concerts_list(route_data, detailed=True, day_number=str(day_number))
            
            return {
                "success": True,
                "day_number": day_number,
                "formatted_route": formatted_route,
                "user_name": user.name or user.email.split('@')[0] if user.email else "Пользователь"
            }
            
        except Exception as e:
            logger.error(f"Bot API Route Day Error: {e}", exc_info=True)
            return {"error": f"Ошибка при получении маршрута на день: {str(e)}", "code": 500}
    
    @staticmethod
    def _format_route_concerts_list(concerts_data, detailed=False, day_number=None):
        """Форматирует список концертов для отображения"""
        try:
            sorted_concerts = concerts_data.get("sorted_concerts", [])
            logger.info(f"Formatting route: {len(sorted_concerts)} concerts, day_number={day_number}")
            
            if not sorted_concerts:
                return "Маршрут не найден или пуст"
            
            # Группируем концерты по дням
            concerts_by_day = {}
            processed_concerts = 0
            for i, concert_data in enumerate(sorted_concerts):
                concert = concert_data['concert']
                if concert.get('datetime'):
                    # Проверяем, является ли datetime строкой или объектом
                    if isinstance(concert['datetime'], str):
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(concert['datetime'].replace('Z', '+00:00'))
                        except Exception as e:
                            logger.warning(f"Failed to parse datetime '{concert['datetime']}': {e}")
                            # Если не удается распарсить, пропускаем концерт
                            continue
                    else:
                        dt = concert['datetime']
                    
                    day = dt.date()
                    if day not in concerts_by_day:
                        concerts_by_day[day] = []
                    concerts_by_day[day].append({
                        'index': i + 1,
                        'time': dt.strftime("%H:%M"),
                        'name': concert.get('name', 'Название не указано'),
                        'hall': concert.get('hall', {}).get('name', 'Зал не указан'),
                        'duration': str(concert.get('duration', 'Длительность не указана')),
                        'genre': concert.get('genre', 'Жанр не указан'),
                        'concert_data': concert_data
                    })
                    processed_concerts += 1
            
            logger.info(f"Processed {processed_concerts} concerts, grouped into {len(concerts_by_day)} days")
            logger.info(f"Available days: {sorted(concerts_by_day.keys())}")
            
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
            
            return concerts_text
            
        except Exception as e:
            logger.error(f"Error formatting route concerts: {e}", exc_info=True)
            return f"Ошибка при форматировании маршрута: {str(e)}" 