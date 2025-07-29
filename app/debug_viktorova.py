#!/usr/bin/env python3
"""
Скрипт для отладки проблемы с композитором Викторова
"""

import sys
import os
sys.path.append('/app')

from app.database.database import get_session
from app.models.concert import Concert
from app.models.composition import Composition, Author, ConcertCompositionLink
from sqlmodel import select
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_viktorova():
    """Отлаживает проблему с композитором Викторова"""
    
    session = next(get_session())
    
    try:
        logger.info("=== ОТЛАДКА КОМПОЗИТОРА ВИКТОРОВА ===")
        
        # 1. Проверяем концерт 80
        logger.info("1. Проверяем концерт 80...")
        concert = session.exec(select(Concert).where(Concert.id == 80)).first()
        if concert:
            logger.info(f"   Концерт 80 найден: {concert.name}")
            logger.info(f"   Дата: {concert.datetime}")
            logger.info(f"   External ID: {concert.external_id}")
        else:
            logger.error("   Концерт 80 не найден!")
            return
        
        # 2. Проверяем композиции концерта 80
        logger.info("2. Проверяем композиции концерта 80...")
        compositions = session.exec(
            select(Composition, Author)
            .join(Author, Composition.author_id == Author.id)
            .join(ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id)
            .where(ConcertCompositionLink.concert_id == 80)
        ).all()
        
        logger.info(f"   Найдено композиций: {len(compositions)}")
        for comp, author in compositions:
            logger.info(f"   - {comp.name} (автор: {author.name}, ID автора: {author.id})")
        
        # 3. Проверяем автора "Викторова"
        logger.info("3. Проверяем автора 'Викторова'...")
        viktorova = session.exec(select(Author).where(Author.name == 'Викторова')).first()
        if viktorova:
            logger.info(f"   Автор 'Викторова' найден (ID: {viktorova.id})")
            
            # Находим все композиции Викторовой
            viktorova_compositions = session.exec(
                select(Composition).where(Composition.author_id == viktorova.id)
            ).all()
            logger.info(f"   Всего композиций Викторовой: {len(viktorova_compositions)}")
            for comp in viktorova_compositions:
                logger.info(f"   - {comp.name}")
        else:
            logger.warning("   Автор 'Викторова' не найден в базе")
            
            # Проверяем похожие имена
            similar_authors = session.exec(
                select(Author).where(Author.name.like('%Виктор%'))
            ).all()
            if similar_authors:
                logger.info("   Найдены похожие авторы:")
                for author in similar_authors:
                    logger.info(f"   - {author.name} (ID: {author.id})")
        
        # 4. Проверяем покупки концерта 80
        logger.info("4. Проверяем покупки концерта 80...")
        from app.models.purchase import Purchase
        purchases = session.exec(
            select(Purchase).where(Purchase.concert_id == 80)
        ).all()
        logger.info(f"   Покупок концерта 80: {len(purchases)}")
        for purchase in purchases:
            logger.info(f"   - Пользователь: {purchase.user_external_id}, Дата: {purchase.purchased_at}")
        
        # 5. Проверяем функцию get_user_purchases_with_details
        logger.info("5. Проверяем функцию get_user_purchases_with_details...")
        from app.services.crud.purchase import get_user_purchases_with_details
        
        # Берем первого пользователя, который купил концерт 80
        if purchases:
            test_user = purchases[0].user_external_id
            logger.info(f"   Тестируем с пользователем: {test_user}")
            
            user_purchases = get_user_purchases_with_details(session, test_user)
            logger.info(f"   Покупок пользователя: {len(user_purchases)}")
            
            # Ищем концерт 80 в покупках пользователя
            concert_80_in_purchases = None
            for purchase in user_purchases:
                if purchase['concert']['id'] == 80:
                    concert_80_in_purchases = purchase
                    break
            
            if concert_80_in_purchases:
                logger.info("   Концерт 80 найден в покупках пользователя!")
                logger.info(f"   Композиций в концерте: {len(concert_80_in_purchases['concert']['compositions'])}")
                for comp in concert_80_in_purchases['concert']['compositions']:
                    author_name = comp['author']['name'] if comp['author'] else 'Нет автора'
                    logger.info(f"   - {comp['name']} (автор: {author_name})")
            else:
                logger.warning("   Концерт 80 не найден в покупках пользователя")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_viktorova() 