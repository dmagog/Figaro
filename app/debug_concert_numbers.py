#!/usr/bin/env python3
"""
Отладочный скрипт для проверки номеров концертов
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_characteristics

def debug_concert_numbers():
    test_user_id = "37138"
    session = next(get_session())
    try:
        print("=== ОТЛАДКА НОМЕРОВ КОНЦЕРТОВ ===")
        
        # Получаем данные концертов
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"\n1. Количество концертов: {len(concerts_data)}")
        
        # Добавляем номера концертов (как в profile_page)
        for i, concert_data in enumerate(concerts_data, 1):
            concert_data['concert_number'] = i
            print(f"   Концерт {i}: ID={concert_data['concert']['id']}, Название={concert_data['concert']['name']}")
        
        # Получаем характеристики
        characteristics = get_user_characteristics(session, test_user_id, concerts_data)
        
        print("\n2. Данные артистов:")
        artists = characteristics.get('artists', [])
        for i, artist in enumerate(artists[:5]):  # Показываем первые 5
            print(f"   {i+1}. {artist['name']}: {artist['count']} концертов")
            if 'concerts' in artist:
                print(f"      Номера концертов: {artist['concerts']}")
        
        print("\n3. Данные произведений:")
        compositions = characteristics.get('compositions', [])
        for i, composition in enumerate(compositions[:5]):  # Показываем первые 5
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
    debug_concert_numbers() 