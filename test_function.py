#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функции get_all_halls_and_genres_with_visit_status
"""
import sys
import os
sys.path.append('/app')

from app.routes.user import get_all_halls_and_genres_with_visit_status
from database.database import get_session
from models.hall import Hall
from models.genre import Genre
from models.concert import Concert

def test_function():
    print("=== ТЕСТИРОВАНИЕ ФУНКЦИИ ===")
    
    try:
        session = next(get_session())
        
        print("1. Проверяем наличие залов в базе данных...")
        halls = session.exec("SELECT * FROM hall").all()
        print(f"Найдено залов: {len(halls)}")
        
        print("2. Проверяем наличие концертов в базе данных...")
        concerts = session.exec("SELECT * FROM concert").all()
        print(f"Найдено концертов: {len(concerts)}")
        
        print("3. Тестируем функцию get_all_halls_and_genres_with_visit_status...")
        result = get_all_halls_and_genres_with_visit_status(session, "37138", [])
        print(f"Результат: {result}")
        
        session.close()
        
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_function() 