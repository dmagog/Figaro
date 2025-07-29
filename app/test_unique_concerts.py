#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы с уникальными концертами
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_purchases_with_details, get_user_unique_concerts_with_details
from app.routes.user import get_user_characteristics, get_all_halls_and_genres_with_visit_status

def test_unique_concerts():
    """Тестирует работу с уникальными концертами"""
    
    # Тестовый пользователь с несколькими покупками
    test_user_id = "37138"  # Используем существующего пользователя
    
    session = next(get_session())
    
    try:
        print("=== ТЕСТ УНИКАЛЬНЫХ КОНЦЕРТОВ ===")
        
        # 1. Получаем все покупки (включая дубликаты)
        print("\n1. Получаем все покупки пользователя...")
        all_purchases = get_user_purchases_with_details(session, test_user_id)
        print(f"   Всего покупок: {len(all_purchases)}")
        
        # Группируем по концертам для анализа
        concert_counts = {}
        for purchase in all_purchases:
            concert_id = purchase['concert']['id']
            concert_counts[concert_id] = concert_counts.get(concert_id, 0) + 1
        
        print(f"   Уникальных концертов: {len(concert_counts)}")
        print(f"   Концерты с несколькими покупками:")
        for concert_id, count in concert_counts.items():
            if count > 1:
                concert_name = next(p['concert']['name'] for p in all_purchases if p['concert']['id'] == concert_id)
                print(f"     - {concert_name} (ID: {concert_id}): {count} покупок")
        
        # 2. Получаем уникальные концерты
        print("\n2. Получаем уникальные концерты...")
        unique_concerts = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"   Уникальных концертов: {len(unique_concerts)}")
        
        # 3. Тестируем расчет характеристик с дубликатами
        print("\n3. Тестируем расчет характеристик с дубликатами...")
        characteristics_with_duplicates = get_user_characteristics(session, test_user_id, all_purchases)
        print(f"   Артистов: {len(characteristics_with_duplicates['artists'])}")
        print(f"   Композиторов: {len(characteristics_with_duplicates['composers'])}")
        print(f"   Произведений: {len(characteristics_with_duplicates['compositions'])}")
        
        # 4. Тестируем расчет характеристик с уникальными концертами
        print("\n4. Тестируем расчет характеристик с уникальными концертами...")
        characteristics_unique = get_user_characteristics(session, test_user_id, unique_concerts)
        print(f"   Артистов: {len(characteristics_unique['artists'])}")
        print(f"   Композиторов: {len(characteristics_unique['composers'])}")
        print(f"   Произведений: {len(characteristics_unique['compositions'])}")
        
        # 5. Сравниваем результаты
        print("\n5. Сравнение результатов:")
        print(f"   Артисты: {len(characteristics_with_duplicates['artists'])} vs {len(characteristics_unique['artists'])}")
        print(f"   Композиторы: {len(characteristics_with_duplicates['composers'])} vs {len(characteristics_unique['composers'])}")
        print(f"   Произведения: {len(characteristics_with_duplicates['compositions'])} vs {len(characteristics_unique['compositions'])}")
        
        # 6. Показываем топ артистов и композиторов
        print("\n6. Топ артистов (с дубликатами):")
        for i, artist in enumerate(characteristics_with_duplicates['artists'][:5], 1):
            print(f"   {i}. {artist['name']}: {artist['count']}")
        
        print("\n   Топ артистов (уникальные концерты):")
        for i, artist in enumerate(characteristics_unique['artists'][:5], 1):
            print(f"   {i}. {artist['name']}: {artist['count']}")
        
        print("\n7. Топ композиторов (с дубликатами):")
        for i, composer in enumerate(characteristics_with_duplicates['composers'][:5], 1):
            print(f"   {i}. {composer['name']}: {composer['count']}")
        
        print("\n   Топ композиторов (уникальные концерты):")
        for i, composer in enumerate(characteristics_unique['composers'][:5], 1):
            print(f"   {i}. {composer['name']}: {composer['count']}")
        
        # 7. Тестируем залы и жанры
        print("\n8. Тестируем залы и жанры...")
        halls_genres_duplicates = get_all_halls_and_genres_with_visit_status(session, test_user_id, all_purchases)
        halls_genres_unique = get_all_halls_and_genres_with_visit_status(session, test_user_id, unique_concerts)
        
        print(f"   Залы (с дубликатами): {len(halls_genres_duplicates['halls'])}")
        print(f"   Залы (уникальные): {len(halls_genres_unique['halls'])}")
        print(f"   Жанры (с дубликатами): {len(halls_genres_duplicates['genres'])}")
        print(f"   Жанры (уникальные): {len(halls_genres_unique['genres'])}")
        
        print("\n=== РЕЗУЛЬТАТ ===")
        if len(characteristics_with_duplicates['artists']) == len(characteristics_unique['artists']):
            print("✅ Количество артистов одинаковое - дубликаты не влияют")
        else:
            print("❌ Количество артистов различается - дубликаты влияют на расчеты")
            
        if len(characteristics_with_duplicates['composers']) == len(characteristics_unique['composers']):
            print("✅ Количество композиторов одинаковое - дубликаты не влияют")
        else:
            print("❌ Количество композиторов различается - дубликаты влияют на расчеты")
            
        if len(characteristics_with_duplicates['compositions']) == len(characteristics_unique['compositions']):
            print("✅ Количество произведений одинаковое - дубликаты не влияют")
        else:
            print("❌ Количество произведений различается - дубликаты влияют на расчеты")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_unique_concerts() 