from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.database.database import get_session
from app.services.bot_api_service import BotApiService
import logging

logger = logging.getLogger(__name__)

bot_api_router = APIRouter(prefix="/bot", tags=["Bot API"])

@bot_api_router.post("/send-template")
async def send_template_message(request: dict, session: Session = Depends(get_session)):
    """API endpoint для бота - отправка сообщения по шаблону через Celery"""
    try:
        telegram_id = request.get("telegram_id")
        template_id = request.get("template_id")
        
        if not telegram_id or not template_id:
            raise HTTPException(status_code=400, detail="Не указаны telegram_id или template_id")
        
        logger.info(f"Bot API request: telegram_id={telegram_id}, template_id={template_id}")
        
        # Используем сервис для обработки
        result = BotApiService.send_template_message(telegram_id, template_id, session)
        
        if result.get("error"):
            raise HTTPException(status_code=result.get("code", 500), detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bot API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@bot_api_router.get("/route-data/{telegram_id}")
async def get_route_data(telegram_id: int, session: Session = Depends(get_session)):
    """API endpoint для бота - получение данных маршрута пользователя"""
    try:
        logger.info(f"Bot API route request: telegram_id={telegram_id}")
        
        # Используем сервис для обработки
        result = BotApiService.get_route_data(telegram_id, session)
        
        if result.get("error"):
            raise HTTPException(status_code=result.get("code", 500), detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bot route API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@bot_api_router.get("/route-day/{telegram_id}/{day_number}")
async def get_route_day(telegram_id: int, day_number: int, session: Session = Depends(get_session)):
    """API endpoint для бота - получение маршрута на конкретный день"""
    try:
        logger.info(f"Bot API route day request: telegram_id={telegram_id}, day={day_number}")
        
        # Используем сервис для обработки
        result = BotApiService.get_route_day(telegram_id, day_number, session)
        
        if result.get("error"):
            raise HTTPException(status_code=result.get("code", 500), detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bot route day API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@bot_api_router.get("/route-days/{telegram_id}")
async def get_route_days(telegram_id: int, session: Session = Depends(get_session)):
    """API endpoint для бота - получение списка доступных дней"""
    try:
        logger.info(f"Bot API route days request: telegram_id={telegram_id}")
        
        # Используем сервис для обработки
        result = BotApiService.get_route_days(telegram_id, session)
        
        if result.get("error"):
            raise HTTPException(status_code=result.get("code", 500), detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in bot route days API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}") 