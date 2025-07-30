#!/usr/bin/env python3
"""
Скрипт для проверки существующих таблиц в базе данных
"""
import sys
import os

# Добавляем путь к app в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def check_tables():
    """Проверяет существующие таблицы"""
    try:
        from sqlmodel import Session, text
        from app.database.database import engine
        
        with Session(engine) as session:
            # Получаем список всех таблиц
            tables_result = session.exec(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
            ).all()
            
            print("Существующие таблицы:")
            for table in tables_result:
                print(f"  - {table[0]}")
                
            # Проверяем, есть ли таблица customer_route_match
            customer_route_match_exists = any(table[0] == 'customer_route_match' for table in tables_result)
            print(f"\nТаблица customer_route_match существует: {customer_route_match_exists}")
                
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    check_tables() 