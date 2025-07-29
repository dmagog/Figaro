#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции get_user_characteristics
"""

import sys
import os
sys.path.append('/app')

from app.database.database import get_session
from app.routes.user import get_user_characteristics
from app.services.crud.purchase import get_user_purchases_with_details
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_characteristics():
    """Тестирует функцию get_user_characteristics"""
    
    # Получаем сессию базы данных
    session = next(get_session())
    
    try:
        # Тестируем с реальным external_id (замените на существующий)
        test_external_id = "test_user_123"  # Замените на реальный ID
        
        logger.info(f"Тестируем с external_id: {test_external_id}")
        
        # Получаем покупки пользователя
        purchases = get_user_purchases_with_details(session, test_external_id)
        logger.info(f"Найдено покупок: {len(purchases)}")
        
        if purchases:
            # Получаем характеристики
            characteristics = get_user_characteristics(session, test_external_id, purchases)
            
            logger.info("=== РЕЗУЛЬТАТЫ ===")
            logger.info(f"Всего концертов: {characteristics['total_concerts']}")
            logger.info(f"Артистов: {len(characteristics['artists'])}")
            logger.info(f"Композиторов: {len(characteristics['composers'])}")
            logger.info(f"Композиций: {len(characteristics['compositions'])}")
            
            logger.info("\n=== ТОП КОМПОЗИТОРЫ ===")
            for composer in characteristics['composers'][:5]:
                logger.info(f"  {composer['name']}: {composer['count']}")
                
            logger.info("\n=== ТОП КОМПОЗИЦИИ ===")
            for composition in characteristics['compositions'][:5]:
                logger.info(f"  {composition['name']}: {composition['count']}")
                
        else:
            logger.warning("Покупки не найдены, попробуйте другой external_id")
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_characteristics() 