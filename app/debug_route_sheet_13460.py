#!/usr/bin/env python3
"""
Отладочный скрипт для проверки данных маршрутного листа пользователя 13460
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_route_sheet, group_concerts_by_day, get_all_festival_days_with_visit_status

def debug_route_sheet_13460():
    test_user_id = "13460"
    session = next(get_session())
    try:
        print("=== ОТЛАДКА МАРШРУТНОГО ЛИСТА ПОЛЬЗОВАТЕЛЯ 13460 ===")
        
        # Получаем данные концертов
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"\n1. Количество концертов: {len(concerts_data)}")
        
        # Получаем дни фестиваля
        festival_days_data = get_all_festival_days_with_visit_status(session, concerts_data)
        print(f"\n2. Дни фестиваля: {len(festival_days_data)}")
        for day in festival_days_data[:5]:  # Показываем первые 5 дней
            print(f"   {day['day']}: {day['visit_count']} концертов")
        
        # Группируем концерты по дням
        concerts_by_day = group_concerts_by_day(concerts_data, festival_days_data)
        print(f"\n3. Концерты по дням:")
        for day_num, day_concerts in concerts_by_day.items():
            print(f"   День {day_num}: {len(day_concerts)} концертов")
            for i, concert_data in enumerate(day_concerts):
                concert = concert_data['concert']
                print(f"     {i+1}. ID={concert['id']}, Название='{concert['name']}'")
                print(f"        Артисты: {[artist['name'] for artist in concert.get('artists', [])]}")
                print(f"        Произведения: {[comp['name'] for comp in concert.get('compositions', [])]}")
        
        # Получаем маршрутный лист
        route_sheet_data = get_user_route_sheet(session, test_user_id, concerts_data, festival_days_data)
        
        print(f"\n4. Данные маршрутного листа:")
        print(f"   Найдено соответствие: {route_sheet_data.get('match', {}).get('found', False)}")
        print(f"   Тип соответствия: {route_sheet_data.get('match', {}).get('match_type', 'unknown')}")
        
        # Проверяем концерты по дням в маршрутном листе
        concerts_by_day_route = route_sheet_data.get('concerts_by_day', {})
        print(f"\n5. Концерты по дням в маршрутном листе:")
        for day_num, day_concerts in concerts_by_day_route.items():
            print(f"   День {day_num}: {len(day_concerts)} концертов")
            for i, concert_data in enumerate(day_concerts):
                concert = concert_data['concert']
                print(f"     {i+1}. ID={concert['id']}, Название='{concert['name']}'")
                print(f"        Артисты: {[artist['name'] for artist in concert.get('artists', [])]}")
                print(f"        Произведения: {[comp['name'] for comp in concert.get('compositions', [])]}")
        
        # Ищем концерт с ID=5 в маршрутном листе
        print(f"\n6. Поиск концерта с ID=5 в маршрутном листе:")
        found_concert_5 = None
        for day_num, day_concerts in concerts_by_day_route.items():
            for concert_data in day_concerts:
                if concert_data['concert']['id'] == 5:
                    found_concert_5 = concert_data
                    print(f"   Найден в дне {day_num}")
                    break
            if found_concert_5:
                break
        
        if found_concert_5:
            concert = found_concert_5['concert']
            print(f"   Название: {concert['name']}")
            print(f"   Артисты: {[artist['name'] for artist in concert.get('artists', [])]}")
            print(f"   Произведения: {[comp['name'] for comp in concert.get('compositions', [])]}")
        else:
            print(f"   Концерт с ID=5 не найден в маршрутном листе")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_route_sheet_13460() 