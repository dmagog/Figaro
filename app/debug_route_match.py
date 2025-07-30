#!/usr/bin/env python3
"""
Скрипт для проверки данных маршрута пользователя
"""
import sys
import os

# Добавляем путь к app в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def check_user_route():
    """Проверяет маршрут пользователя"""
    try:
        from sqlmodel import Session, select
        from app.database.database import engine
        from app.models import CustomerRouteMatch, Route, User
        
        with Session(engine) as session:
            # Проверяем пользователя
            user = session.exec(select(User).where(User.external_id == "13460")).first()
            if user:
                print(f"Пользователь найден: ID={user.id}, external_id={user.external_id}")
            else:
                print("Пользователь с external_id=13460 не найден")
                return
            
            # Проверяем маршрут пользователя
            route_match = session.exec(
                select(CustomerRouteMatch).where(CustomerRouteMatch.user_external_id == "13460")
            ).first()
            
            if route_match:
                print(f"Запись CustomerRouteMatch найдена:")
                print(f"  - found: {route_match.found}")
                print(f"  - match_type: {route_match.match_type}")
                print(f"  - best_route_id: {route_match.best_route_id}")
                print(f"  - customer_concerts: {route_match.customer_concerts}")
                
                if route_match.found and route_match.best_route_id:
                    # Получаем маршрут
                    route = session.exec(
                        select(Route).where(Route.id == route_match.best_route_id)
                    ).first()
                    
                    if route:
                        print(f"Маршрут найден:")
                        print(f"  - ID: {route.id}")
                        print(f"  - Sostav: {route.Sostav}")
                        print(f"  - Concerts: {route.Concerts}")
                        print(f"  - Days: {route.Days}")
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
    check_user_route() 