#!/usr/bin/env python3
"""
Тест интеграции офф-программы в маршрутный лист
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_off_program_integration():
    """Тестирует интеграцию офф-программы в маршрутный лист"""
    
    try:
        session = next(get_session())
        
        print("🔍 Проверяем данные офф-программы...")
        
        # Получаем все мероприятия офф-программы
        off_program_events = session.exec(select(OffProgram)).all()
        print(f"📊 Найдено {len(off_program_events)} мероприятий офф-программы")
        
        if not off_program_events:
            print("❌ Нет данных офф-программы для тестирования")
            return False
        
        # Получаем несколько концертов для тестирования
        concerts = session.exec(select(Concert).limit(5)).all()
        print(f"🎵 Найдено {len(concerts)} концертов для тестирования")
        
        if len(concerts) < 2:
            print("❌ Недостаточно концертов для тестирования")
            return False
        
        # Создаем тестовые данные концертов
        test_concerts = []
        for i, concert in enumerate(concerts[:2]):
            # Получаем зал концерта
            hall = session.exec(select(Hall).where(Hall.id == concert.hall_id)).first()
            
            concert_data = {
                'concert': {
                    'id': concert.id,
                    'name': concert.name,
                    'datetime': concert.datetime,
                    'duration': concert.duration,
                    'hall': {
                        'id': hall.id if hall else None,
                        'name': hall.name if hall else 'Неизвестный зал'
                    } if hall else None
                }
            }
            test_concerts.append(concert_data)
        
        print(f"\n🎯 Тестируем поиск доступных мероприятий между концертами...")
        print(f"Концерт 1: {test_concerts[0]['concert']['name']} в {test_concerts[0]['concert']['datetime']}")
        print(f"Концерт 2: {test_concerts[1]['concert']['name']} в {test_concerts[1]['concert']['datetime']}")
        
        # Тестируем функцию поиска
        available_events = find_available_off_program_events(
            session, 
            test_concerts[0], 
            test_concerts[1]
        )
        
        print(f"\n📋 Найдено {len(available_events)} доступных мероприятий офф-программы:")
        
        for i, event in enumerate(available_events, 1):
            print(f"\n  {i}. {event['event_name']}")
            print(f"     Время: {event['event_date_display']}")
            print(f"     Длительность: {event['duration']}")
            print(f"     Зал: {event['hall_name']}")
            print(f"     Формат: {event['format']}")
            print(f"     Рекомендуется: {'Да' if event['recommend'] else 'Нет'}")
            print(f"     Время перехода к мероприятию: ~{event['walk_time_to_event']}м")
            print(f"     Время перехода от мероприятия: ~{event['walk_time_from_event']}м")
            print(f"     Общее время переходов: ~{event['total_walk_time']}м")
            print(f"     Доступное время: {event['available_time']}м")
            print(f"     Длительность мероприятия: {event['event_duration_minutes']}м")
        
        if available_events:
            print(f"\n✅ Тест пройден успешно! Найдено {len(available_events)} доступных мероприятий")
        else:
            print(f"\n⚠️ Доступных мероприятий не найдено (это может быть нормально)")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Запуск теста интеграции офф-программы...")
    success = test_off_program_integration()
    if success:
        print("\n🎉 Тест завершен успешно!")
    else:
        print("\n💥 Тест завершен с ошибками!")
        sys.exit(1) 