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
    logger.info(f"[Celery] Отправка сообщения пользователю {telegram_id}: {text} (file: {file_path}, type: {file_type}, parse_mode: {parse_mode})")
    
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