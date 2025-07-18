#!/usr/bin/env python3
"""
Тест для проверки функциональности офф-программы до первого и после последнего концерта
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import (
    find_available_off_program_events_before_first_concert,
    find_available_off_program_events_after_last_concert
)
from datetime import datetime, timedelta
from models import Concert, Hall, OffProgram
from sqlalchemy import select

def test_off_program_before_first_concert():
    """Тест поиска офф-программы до первого концерта"""
    print("🧪 Тестируем поиск офф-программы до первого концерта...")
    
    session = next(get_session())
    
    try:
        # Создаем тестовые данные
        # Создаем зал
        hall = Hall(
            name="Тестовый зал",
            address="Тестовая улица, 1",
            capacity=100,
            concert_count=0
        )
        session.add(hall)
        session.commit()
        session.refresh(hall)
        
        # Создаем концерт в 15:00
        concert_datetime = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        concert = Concert(
            external_id=1001,
            name="Тестовый концерт",
            datetime=concert_datetime,
            duration=timedelta(hours=1, minutes=30),
            hall_id=hall.id,
            genre="Классическая музыка"
        )
        session.add(concert)
        session.commit()
        session.refresh(concert)
        
        # Создаем мероприятие офф-программы в 13:00 (за 2 часа до концерта)
        off_program_datetime = concert_datetime - timedelta(hours=2)
        off_program = OffProgram(
            event_num=2001,
            event_name="Тестовая лекция",
            description="Тестовое описание",
            event_date=off_program_datetime,
            event_long="01:00",  # 1 час
            hall_name="Инфоцентр",
            format="Лекция",
            recommend=True
        )
        session.add(off_program)
        session.commit()
        session.refresh(off_program)
        
        # Создаем концерт в формате словаря для функции
        concert_dict = {
            'concert': {
                'datetime': concert_datetime,
                'hall': {'id': hall.id}
            }
        }
        
        # Тестируем функцию
        events = find_available_off_program_events_before_first_concert(session, concert_dict)
        
        print(f"✅ Найдено мероприятий до первого концерта: {len(events)}")
        
        if events:
            event = events[0]
            print(f"   📅 Время: {event['event_date_display']}")
            print(f"   🎯 Название: {event['event_name']}")
            print(f"   ⏱️ Длительность: {event['duration']}")
            print(f"   📍 Зал: {event['hall_name']}")
            print(f"   🚶🏼‍➡️ Время перехода: {event['walk_time_to_concert']} мин")
            print(f"   🕐 Доступное время: {event['available_time']} мин")
            print(f"   🏷️ Тип: {event['type']}")
        else:
            print("   ❌ Мероприятия не найдены")
        
        # Очистка
        session.delete(off_program)
        session.delete(concert)
        session.delete(hall)
        session.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def test_off_program_after_last_concert():
    """Тест поиска офф-программы после последнего концерта"""
    print("\n🧪 Тестируем поиск офф-программы после последнего концерта...")
    
    session = next(get_session())
    
    try:
        # Создаем тестовые данные
        # Создаем зал
        hall = Hall(
            name="Тестовый зал",
            address="Тестовая улица, 1",
            capacity=100,
            concert_count=0
        )
        session.add(hall)
        session.commit()
        session.refresh(hall)
        
        # Создаем концерт в 19:00
        concert_datetime = datetime.now().replace(hour=19, minute=0, second=0, microsecond=0)
        concert = Concert(
            external_id=1002,
            name="Тестовый концерт",
            datetime=concert_datetime,
            duration=timedelta(hours=1, minutes=30),
            hall_id=hall.id,
            genre="Классическая музыка"
        )
        session.add(concert)
        session.commit()
        session.refresh(concert)
        
        # Создаем мероприятие офф-программы в 21:00 (после концерта)
        off_program_datetime = concert_datetime + timedelta(hours=2)  # 21:00
        off_program = OffProgram(
            event_num=2002,
            event_name="Вечерняя лекция",
            description="Тестовое описание вечерней лекции",
            event_date=off_program_datetime,
            event_long="01:00",  # 1 час
            hall_name="Инфоцентр",
            format="Лекция",
            recommend=True
        )
        session.add(off_program)
        session.commit()
        session.refresh(off_program)
        
        # Создаем концерт в формате словаря для функции
        concert_dict = {
            'concert': {
                'datetime': concert_datetime,
                'duration': timedelta(hours=1, minutes=30),
                'hall': {'id': hall.id}
            }
        }
        
        # Тестируем функцию
        events = find_available_off_program_events_after_last_concert(session, concert_dict)
        
        print(f"✅ Найдено мероприятий после последнего концерта: {len(events)}")
        
        if events:
            event = events[0]
            print(f"   📅 Время: {event['event_date_display']}")
            print(f"   🎯 Название: {event['event_name']}")
            print(f"   ⏱️ Длительность: {event['duration']}")
            print(f"   📍 Зал: {event['hall_name']}")
            print(f"   🚶🏼‍➡️ Время перехода: {event['walk_time_from_concert']} мин")
            print(f"   🕐 Доступное время: {event['available_time']} мин")
            print(f"   🏷️ Тип: {event['type']}")
        else:
            print("   ❌ Мероприятия не найдены")
        
        # Очистка
        session.delete(off_program)
        session.delete(concert)
        session.delete(hall)
        session.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def test_real_data():
    """Тест с реальными данными из базы"""
    print("\n🧪 Тестируем с реальными данными...")
    
    session = next(get_session())
    
    try:
        # Получаем первый концерт из базы
        first_concert = session.exec(
            select(Concert).order_by(Concert.datetime)
        ).first()
        
        if not first_concert:
            print("❌ Нет концертов в базе данных")
            return False
        
        # Получаем последний концерт из базы
        last_concert = session.exec(
            select(Concert).order_by(Concert.datetime.desc())
        ).first()
        
        if not last_concert:
            print("❌ Нет концертов в базе данных")
            return False
        
        # Получаем зал для первого концерта
        first_hall = session.exec(
            select(Hall).where(Hall.id == first_concert.hall_id)
        ).first()
        
        # Получаем зал для последнего концерта
        last_hall = session.exec(
            select(Hall).where(Hall.id == last_concert.hall_id)
        ).first()
        
        # Создаем концерты в формате словаря
        first_concert_dict = {
            'concert': {
                'datetime': first_concert.datetime,
                'hall': {'id': first_concert.hall_id} if first_concert.hall_id else None
            }
        }
        
        last_concert_dict = {
            'concert': {
                'datetime': last_concert.datetime,
                'duration': last_concert.duration,
                'hall': {'id': last_concert.hall_id} if last_concert.hall_id else None
            }
        }
        
        print(f"📅 Первый концерт: {first_concert.name} в {first_concert.datetime.strftime('%H:%M')}")
        print(f"📅 Последний концерт: {last_concert.name} в {last_concert.datetime.strftime('%H:%M')}")
        
        # Тестируем поиск офф-программы до первого концерта
        before_events = find_available_off_program_events_before_first_concert(session, first_concert_dict)
        print(f"✅ Найдено мероприятий до первого концерта: {len(before_events)}")
        
        # Тестируем поиск офф-программы после последнего концерта
        after_events = find_available_off_program_events_after_last_concert(session, last_concert_dict)
        print(f"✅ Найдено мероприятий после последнего концерта: {len(after_events)}")
        
        if before_events:
            print("\n📋 Мероприятия до первого концерта:")
            for event in before_events[:3]:  # Показываем первые 3
                print(f"   • {event['event_date_display']} - {event['event_name']} ({event['duration']})")
        
        if after_events:
            print("\n📋 Мероприятия после последнего концерта:")
            for event in after_events[:3]:  # Показываем первые 3
                print(f"   • {event['event_date_display']} - {event['event_name']} ({event['duration']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте с реальными данными: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Запуск тестов расширенной функциональности офф-программы")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Тест 1: Офф-программа до первого концерта
    if test_off_program_before_first_concert():
        success_count += 1
    
    # Тест 2: Офф-программа после последнего концерта
    if test_off_program_after_last_concert():
        success_count += 1
    
    # Тест 3: Реальные данные
    if test_real_data():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Результаты тестирования: {success_count}/{total_tests} тестов прошли успешно")
    
    if success_count == total_tests:
        print("🎉 Все тесты прошли успешно!")
    else:
        print("⚠️ Некоторые тесты не прошли") 