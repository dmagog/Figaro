#!/usr/bin/env python3
"""
Отладочный скрипт для проверки данных маршрутного листа
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_route_sheet, calculate_route_statistics

def debug_route_stats():
    """Отлаживает данные маршрутного листа"""
    
    # Тестовый пользователь
    test_user_id = "37138"
    
    session = next(get_session())
    
    try:
        print("=== ОТЛАДКА ДАННЫХ МАРШРУТНОГО ЛИСТА ===")
        
        # 1. Получаем уникальные концерты
        print("\n1. Получаем уникальные концерты...")
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        print(f"   Найдено концертов: {len(concerts_data)}")
        
        # 2. Получаем полный маршрутный лист
        print("\n2. Получаем маршрутный лист...")
        route_sheet = get_user_route_sheet(session, test_user_id, concerts_data)
        
        print("\n3. Данные summary:")
        summary = route_sheet.get('summary', {})
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        # 4. Проверяем calculate_route_statistics отдельно
        print("\n4. Проверяем calculate_route_statistics...")
        concerts_by_day = route_sheet.get('concerts_by_day', {})
        route_stats = calculate_route_statistics(session, concerts_data, concerts_by_day)
        
        print("\n5. Результат calculate_route_statistics:")
        for key, value in route_stats.items():
            print(f"   {key}: {value}")
        
        # 6. Проверяем структуру данных концертов
        print("\n6. Структура данных концертов:")
        if concerts_data:
            sample_concert = concerts_data[0]['concert']
            print(f"   Ключи концерта: {list(sample_concert.keys())}")
            print(f"   Длительность: {sample_concert.get('duration')} (тип: {type(sample_concert.get('duration'))})")
            print(f"   Зал: {sample_concert.get('hall')}")
        
        # 7. Проверяем переходы
        print("\n7. Проверяем переходы:")
        total_transitions = 0
        for day_concerts in concerts_by_day.values():
            for concert in day_concerts:
                if concert.get('transition_info'):
                    transition = concert['transition_info']
                    print(f"   Переход: {transition}")
                    if transition.get('walk_time'):
                        total_transitions += transition['walk_time']
        
        print(f"   Общее время переходов: {total_transitions} минут")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_route_stats() 