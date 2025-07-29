#!/usr/bin/env python3
"""
Отладочный скрипт для проверки данных в шаблоне
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user import get_user_route_sheet

def debug_template_data():
    """Отлаживает данные для шаблона"""
    
    # Тестовый пользователь
    test_user_id = "37138"
    
    session = next(get_session())
    
    try:
        print("=== ОТЛАДКА ДАННЫХ ДЛЯ ШАБЛОНА ===")
        
        # Получаем данные
        concerts_data = get_user_unique_concerts_with_details(session, test_user_id)
        route_sheet = get_user_route_sheet(session, test_user_id, concerts_data)
        
        print("\n1. Структура route_sheet:")
        print(f"   Ключи: {list(route_sheet.keys())}")
        
        print("\n2. Данные summary:")
        summary = route_sheet.get('summary', {})
        print(f"   Ключи summary: {list(summary.keys())}")
        
        print("\n3. Значения полей:")
        fields_to_check = [
            'total_days', 'total_concerts', 'total_halls', 'total_genres',
            'total_concert_time_minutes', 'total_walk_time_minutes', 'total_distance_km',
            'unique_compositions', 'unique_authors', 'unique_artists'
        ]
        
        for field in fields_to_check:
            value = summary.get(field)
            print(f"   {field}: {value} (тип: {type(value)})")
        
        print("\n4. Проверка на None/пустые значения:")
        for field in fields_to_check:
            value = summary.get(field)
            if value is None or value == '':
                print(f"   ❌ {field}: {value}")
            else:
                print(f"   ✅ {field}: {value}")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_template_data() 