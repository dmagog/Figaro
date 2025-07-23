from .celery_worker import celery_app
import os
from dotenv import load_dotenv
import asyncio
from bot.utils import send_telegram_message as tg_send
from celery.utils.log import get_task_logger

load_dotenv()
logger = get_task_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_telegram_message(self, telegram_id: int, text: str = None, file_path: str = None, file_type: str = None):
    logger.info(f"[Celery] Отправка сообщения пользователю {telegram_id}: {text} (file: {file_path}, type: {file_type})")
    try:
        result = asyncio.run(tg_send(telegram_id, text, file_path, file_type))
        return result
    except Exception as e:
        logger.error(f"[Celery] Ошибка отправки сообщения: {e}")
        # Retry при ошибке 429 или любой Exception
        if hasattr(e, 'response') and getattr(e.response, 'status', None) == 429:
            logger.warning("429 Too Many Requests: повторная попытка...")
            raise self.retry(exc=e, countdown=30)
        raise self.retry(exc=e) 