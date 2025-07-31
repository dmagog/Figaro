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