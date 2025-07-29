#!/usr/bin/env python3
"""
Тестовый скрипт для проверки данных залов и жанров
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_purchases_with_details

def debug_halls_and_genres():
    """Проверяем данные залов и жанров в концертах пользователя"""
    
    # Используем реальный external_id
    test_external_id = "37138"
    
    session = next(get_session())
    try:
        print(f"Получаем данные для пользователя: {test_external_id}")
        
        # Получаем покупки с деталями
        purchases_data = get_user_purchases_with_details(session, test_external_id)
        
        print(f"Найдено покупок: {len(purchases_data)}")
        
        if not purchases_data:
            print("Нет данных о покупках!")
            return
        
        # Проверяем первые несколько концертов
        for i, purchase_data in enumerate(purchases_data[:3]):
            concert = purchase_data['concert']
            print(f"\nКонцерт {i+1} (ID: {concert.get('id')}):")
            print(f"  Название: {concert.get('name')}")
            print(f"  Жанр: {concert.get('genre')}")
            print(f"  Зал: {concert.get('hall')}")
            
            if concert.get('hall'):
                print(f"    ID зала: {concert['hall'].get('id')}")
                print(f"    Название зала: {concert['hall'].get('name')}")
                print(f"    Адрес: {concert['hall'].get('address')}")
            else:
                print("    Зал не найден!")
        
        # Проверяем все уникальные жанры
        genres = set()
        halls = set()
        
        for purchase_data in purchases_data:
            concert = purchase_data['concert']
            if concert.get('genre'):
                genres.add(concert['genre'])
            if concert.get('hall') and concert['hall'].get('name'):
                halls.add(concert['hall']['name'])
        
        print(f"\nУникальные жанры ({len(genres)}): {sorted(list(genres))}")
        print(f"Уникальные залы ({len(halls)}): {sorted(list(halls))}")
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_halls_and_genres() 