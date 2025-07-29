#!/usr/bin/env python3
"""
Отладочный скрипт для проверки данных характеристик
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_characteristics, get_all_halls_and_genres_with_visit_status

def debug_characteristics():
    test_user_id = "37138"
    session = next(get_session())
    try:
        print("=== ОТЛАДКА ДАННЫХ ХАРАКТЕРИСТИК ===")
        
        # Получаем данные концертов
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"\n1. Количество концертов: {len(concerts_data)}")
        
        # Добавляем номера концертов
        for i, concert_data in enumerate(concerts_data, 1):
            concert_data['concert_number'] = i
        
        # Получаем характеристики
        characteristics = get_user_characteristics(session, test_user_id, concerts_data)
        
        print("\n2. Структура характеристик:")
        print(f"   Ключи: {list(characteristics.keys())}")
        print(f"   total_concerts: {characteristics.get('total_concerts', 0)}")
        
        print("\n3. Данные залов:")
        halls = characteristics.get('halls', [])
        print(f"   Количество залов: {len(halls)}")
        for i, hall in enumerate(halls[:3]):  # Показываем первые 3
            print(f"   {i+1}. {hall['name']}: {hall['visit_count']} концертов")
            if 'concerts' in hall:
                print(f"      Номера концертов: {hall['concerts']}")
        
        print("\n4. Данные жанров:")
        genres = characteristics.get('genres', [])
        print(f"   Количество жанров: {len(genres)}")
        for i, genre in enumerate(genres[:3]):  # Показываем первые 3
            print(f"   {i+1}. {genre['name']}: {genre['visit_count']} концертов")
            if 'concerts' in genre:
                print(f"      Номера концертов: {genre['concerts']}")
        
        print("\n5. Данные артистов:")
        artists = characteristics.get('artists', [])
        print(f"   Количество артистов: {len(artists)}")
        for i, artist in enumerate(artists[:3]):  # Показываем первые 3
            print(f"   {i+1}. {artist['name']}: {artist['count']} концертов")
            if 'concerts' in artist:
                print(f"      Номера концертов: {artist['concerts']}")
        
        print("\n6. Данные композиторов:")
        composers = characteristics.get('composers', [])
        print(f"   Количество композиторов: {len(composers)}")
        for i, composer in enumerate(composers[:3]):  # Показываем первые 3
            print(f"   {i+1}. {composer['name']}: {composer['count']} произведений")
            if 'concerts' in composer:
                print(f"      Номера концертов: {composer['concerts']}")
        
        print("\n7. Данные произведений:")
        compositions = characteristics.get('compositions', [])
        print(f"   Количество произведений: {len(compositions)}")
        for i, composition in enumerate(compositions[:3]):  # Показываем первые 3
            print(f"   {i+1}. {composition['name']}: {composition['count']} исполнений")
            if 'concerts' in composition:
                print(f"      Номера концертов: {composition['concerts']}")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_characteristics() 