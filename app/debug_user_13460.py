#!/usr/bin/env python3
"""
Отладочный скрипт для проверки данных пользователя с external_id=13460
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_characteristics

def debug_user_13460():
    test_user_id = "13460"
    session = next(get_session())
    try:
        print("=== ОТЛАДКА ПОЛЬЗОВАТЕЛЯ 13460 ===")
        
        # Получаем данные концертов
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"\n1. Количество концертов: {len(concerts_data)}")
        
        # Показываем все концерты с их ID и артистами
        print("\n2. Концерты пользователя:")
        for i, concert_data in enumerate(concerts_data):
            concert = concert_data['concert']
            print(f"   {i+1}. ID={concert['id']}, Название='{concert['name']}'")
            print(f"      Артисты: {[artist['name'] for artist in concert.get('artists', [])]}")
            print(f"      Произведения: {[comp['name'] for comp in concert.get('compositions', [])]}")
            print()
        
        # Ищем концерт с ID=5
        concert_5 = None
        for concert_data in concerts_data:
            if concert_data['concert']['id'] == 5:
                concert_5 = concert_data
                break
        
        if concert_5:
            print(f"\n3. Концерт с ID=5:")
            print(f"   Название: {concert_5['concert']['name']}")
            print(f"   Артисты: {[artist['name'] for artist in concert_5['concert'].get('artists', [])]}")
            print(f"   Произведения: {[comp['name'] for comp in concert_5['concert'].get('compositions', [])]}")
        else:
            print(f"\n3. Концерт с ID=5 не найден в покупках пользователя")
        
        # Получаем характеристики
        characteristics = get_user_characteristics(session, test_user_id, concerts_data)
        
        print(f"\n4. Артисты в характеристиках:")
        artists = characteristics.get('artists', [])
        for i, artist in enumerate(artists[:10]):  # Показываем первые 10
            print(f"   {i+1}. {artist['name']}: {artist['count']} концертов")
            if 'concerts' in artist:
                print(f"      Номера концертов: {artist['concerts']}")
        
        print(f"\n5. Произведения в характеристиках:")
        compositions = characteristics.get('compositions', [])
        for i, composition in enumerate(compositions[:10]):  # Показываем первые 10
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
    debug_user_13460() 