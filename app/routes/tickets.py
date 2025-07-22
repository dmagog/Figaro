from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from database.database import get_session
from sqlmodel import Session, select
from models import Concert
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone
from services.crud.tickets import tickets_service

logger = logging.getLogger(__name__)
tickets_route = APIRouter()





# Глобальный экземпляр сервиса
ticket_service = tickets_service


@tickets_route.get("/api/tickets/availability")
async def get_tickets_availability(
    concert_ids: str,  # Список ID через запятую
    session: Session = Depends(get_session)
) -> JSONResponse:
    """
    Получает информацию о доступности билетов для концертов
    
    Args:
        concert_ids: Список ID концертов через запятую (например: "1,2,3,4")
        session: Сессия базы данных
        
    Returns:
        JSONResponse с информацией о билетах
    """
    try:
        # Парсим список ID концертов
        try:
            concert_id_list = [int(x.strip()) for x in concert_ids.split(',') if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Некорректный формат concert_ids")
        
        if not concert_id_list:
            raise HTTPException(status_code=400, detail="Список ID концертов пуст")
        
        # Проверяем, что концерты существуют в базе
        existing_concerts = session.exec(
            select(Concert).where(Concert.id.in_(concert_id_list))
        ).all()
        
        existing_ids = {c.id for c in existing_concerts}
        missing_ids = set(concert_id_list) - existing_ids
        
        if missing_ids:
            logger.warning(f"Концерты с ID {missing_ids} не найдены в базе")
        
        # Получаем информацию о билетах только для существующих концертов
        tickets_info = ticket_service.get_concerts_availability(session, list(existing_ids))
        
        # Добавляем информацию о концертах
        result = {}
        for concert in existing_concerts:
            concert_info = tickets_info.get(concert.id, {})
            result[concert.id] = {
                "concert_id": concert.id,
                "concert_name": concert.name,
                "concert_datetime": concert.datetime.isoformat() if concert.datetime else None,
                "available": concert_info.get("available", False),
                "tickets_left": concert_info.get("tickets_left", 0),
                "total_seats": concert_info.get("total_seats", 0),
                "last_updated": concert_info.get("last_updated", datetime.now(timezone.utc)).isoformat(),
                "fallback": concert_info.get("fallback", False)
            }
        
        return JSONResponse({
            "success": True,
            "data": result,
            "missing_concerts": list(missing_ids) if missing_ids else None,
            "total_concerts": len(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о билетах: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@tickets_route.get("/api/tickets/availability/{concert_id}")
async def get_concert_tickets_availability(
    concert_id: int,
    session: Session = Depends(get_session)
) -> JSONResponse:
    """
    Получает информацию о доступности билетов для конкретного концерта
    
    Args:
        concert_id: ID концерта
        session: Сессия базы данных
        
    Returns:
        JSONResponse с информацией о билетах
    """
    try:
        # Проверяем, что концерт существует
        concert = session.exec(select(Concert).where(Concert.id == concert_id)).first()
        if not concert:
            raise HTTPException(status_code=404, detail=f"Концерт с ID {concert_id} не найден")
        
        # Получаем информацию о билетах
        tickets_info = ticket_service.get_concerts_availability(session, [concert_id])
        concert_info = tickets_info.get(concert_id, {})
        
        return JSONResponse({
            "success": True,
            "data": {
                "concert_id": concert.id,
                "concert_name": concert.name,
                "concert_datetime": concert.datetime.isoformat() if concert.datetime else None,
                "available": concert_info.get("available", False),
                "tickets_left": concert_info.get("tickets_left", 0),
                "total_seats": concert_info.get("total_seats", 0),
                "last_updated": concert_info.get("last_updated", datetime.now(timezone.utc)).isoformat(),
                "fallback": concert_info.get("fallback", False)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о билетах для концерта {concert_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@tickets_route.get("/api/tickets/status")
async def get_tickets_service_status() -> JSONResponse:
    """
    Проверяет статус сервиса продажи билетов
    
    Returns:
        JSONResponse со статусом сервиса
    """
    try:
        # В реальной системе здесь была бы проверка доступности API
        # Пример:
        # async with httpx.AsyncClient(timeout=5.0) as client:
        #     response = await client.get(f"{ticket_service.api_base_url}/health")
        #     is_healthy = response.status_code == 200
        
        # Заглушка для демонстрации
        is_healthy = True
        
        return JSONResponse({
            "success": True,
            "service": "tickets_api",
            "status": "healthy" if is_healthy else "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0"
        })
        
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса сервиса билетов: {e}")
        return JSONResponse({
            "success": False,
            "service": "tickets_api",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)


@tickets_route.get("/api/tickets/stats")
async def get_tickets_service_stats() -> JSONResponse:
    """
    Получает статистику сервиса билетов
    
    Returns:
        JSONResponse со статистикой сервиса
    """
    try:
        # Получаем статистику кэша
        cache_stats = tickets_service.get_cache_stats()
        
        return JSONResponse({
            "success": True,
            "service": "tickets_service",
            "cache_stats": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики сервиса билетов: {e}")
        return JSONResponse({
            "success": False,
            "service": "tickets_service",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500)


@tickets_route.post("/api/routes/update-availability")
async def update_routes_availability(session: Session = Depends(get_session)) -> JSONResponse:
    """
    Обновляет доступные маршруты на основе текущего статуса билетов концертов
    
    Returns:
        JSONResponse с результатом обновления
    """
    try:
        logger.info("Запрос на обновление доступных маршрутов...")
        
        # Импортируем функцию обновления маршрутов
        from services.crud.route_service import update_available_routes
        
        # Обновляем доступные маршруты
        result = update_available_routes(session)
        
        logger.info(f"Обновление доступных маршрутов завершено: {result}")
        
        return JSONResponse({
            "success": True,
            "message": "Доступные маршруты успешно обновлены",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении доступных маршрутов: {e}")
        return JSONResponse({
            "success": False,
            "message": "Ошибка при обновлении доступных маршрутов",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=500) 