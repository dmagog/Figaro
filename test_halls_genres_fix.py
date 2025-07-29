#!/usr/bin/env python3
"""
Тестовый скрипт для проверки и исправления функции залов и жанров
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.services.crud.purchase import get_user_purchases_with_details

def test_halls_and_genres_fix():
    """Тестируем исправленную логику для залов и жанров"""
    
    # Используем реальный external_id
    test_external_id = "37138"
    
    session = next(get_session())
    try:
        print(f"Получаем данные для пользователя: {test_external_id}")
        
        # Получаем покупки с деталями
        purchases_data = get_user_purchases_with_details(session, test_external_id)
        
        print(f"Найдено покупок: {len(purchases_data)}")
        
        if not purchases_data:
            print("Нет данных о покупках!")
            return
        
        # Имитируем исправленную логику функции get_all_halls_and_genres_with_visit_status
        from collections import Counter
        
        # Получаем все уникальные жанры и залы из концертов пользователя
        all_genres = set()
        all_halls = set()
        
        # Собираем уникальные жанры и залы из концертов пользователя
        for concert_data in purchases_data:
            concert = concert_data['concert']
            
            # Добавляем жанр
            if concert.get('genre'):
                all_genres.add(concert['genre'])
            
            # Добавляем зал
            if concert.get('hall') and concert['hall'].get('name'):
                all_halls.add(concert['hall']['name'])
        
        # Преобразуем в списки
        all_genres = list(all_genres)
        all_halls = list(all_halls)
        
        print(f"\nУникальные жанры ({len(all_genres)}): {sorted(all_genres)}")
        print(f"Уникальные залы ({len(all_halls)}): {sorted(all_halls)}")
        
        # Счетчики посещений залов и жанров
        halls_counter = Counter()
        genres_counter = Counter()
        
        # Обрабатываем концерты пользователя
        for concert_data in purchases_data:
            concert = concert_data['concert']
            
            # Добавляем зал в счетчик
            if concert.get('hall') and concert['hall'].get('name'):
                halls_counter[concert['hall']['name']] += 1
            
            # Добавляем жанр в счетчик
            if concert.get('genre'):
                genres_counter[concert['genre']] += 1
        
        # Формируем список всех залов с количеством посещений
        halls_with_status = []
        for hall_name in all_halls:
            visit_count = halls_counter.get(hall_name, 0)
            halls_with_status.append({
                "name": hall_name,
                "visit_count": visit_count,
                "is_visited": visit_count > 0,
                "address": "",  # Адрес не доступен из данных концертов
                "seats": 0      # Количество мест не доступно из данных концертов
            })
        
        # Сортируем залы по убыванию количества посещений
        halls_with_status.sort(key=lambda x: x['visit_count'], reverse=True)
        
        # Формируем список всех жанров с количеством посещений
        genres_with_status = []
        for genre in all_genres:
            visit_count = genres_counter.get(genre, 0)
            genres_with_status.append({
                "name": genre,
                "visit_count": visit_count,
                "is_visited": visit_count > 0
            })
        
        # Сортируем жанры по убыванию количества посещений
        genres_with_status.sort(key=lambda x: x['visit_count'], reverse=True)
        
        result = {
            "halls": halls_with_status,
            "genres": genres_with_status
        }
        
        print(f"\nРезультат функции:")
        print(f"Залы ({len(result['halls'])}):")
        for hall in result['halls']:
            print(f"  - {hall['name']}: {hall['visit_count']} посещений")
        
        print(f"\nЖанры ({len(result['genres'])}):")
        for genre in result['genres']:
            print(f"  - {genre['name']}: {genre['visit_count']} посещений")
        
        return result
        
    finally:
        session.close()

if __name__ == "__main__":
    test_halls_and_genres_fix() 