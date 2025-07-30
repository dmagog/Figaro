#!/usr/bin/env python3
"""
Упрощенный скрипт для проверки данных маршрута пользователя
"""
import sys
import os

# Добавляем путь к app в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def check_user_route_simple():
    """Проверяет маршрут пользователя через SQL"""
    try:
        from sqlmodel import Session, text
        from app.database.database import engine
        
        with Session(engine) as session:
            # Проверяем пользователя
            user_result = session.exec(text("SELECT id, external_id FROM \"user\" WHERE external_id = '13460'")).first()
            if user_result:
                print(f"Пользователь найден: ID={user_result[0]}, external_id={user_result[1]}")
            else:
                print("Пользователь с external_id=13460 не найден")
                return
            
            # Проверяем маршрут пользователя
            route_match_result = session.exec(
                text("SELECT found, match_type, best_route_id, customer_concerts FROM customer_route_match WHERE user_external_id = '13460'")
            ).first()
            
            if route_match_result:
                found, match_type, best_route_id, customer_concerts = route_match_result
                print(f"Запись CustomerRouteMatch найдена:")
                print(f"  - found: {found}")
                print(f"  - match_type: {match_type}")
                print(f"  - best_route_id: {best_route_id}")
                print(f"  - customer_concerts: {customer_concerts}")
                
                if found and best_route_id:
                    # Получаем маршрут
                    route_result = session.exec(
                        text(f"SELECT id, \"Sostav\", \"Concerts\", \"Days\" FROM route WHERE id = {best_route_id}")
                    ).first()
                    
                    if route_result:
                        route_id, sostav, concerts, days = route_result
                        print(f"Маршрут найден:")
                        print(f"  - ID: {route_id}")
                        print(f"  - Sostav: {sostav}")
                        print(f"  - Concerts: {concerts}")
                        print(f"  - Days: {days}")
                    else:
                        print("Маршрут не найден в базе")
                else:
                    print("Маршрут не найден для пользователя (found=False или best_route_id=None)")
            else:
                print("Запись CustomerRouteMatch не найдена для пользователя")
                
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    check_user_route_simple() 