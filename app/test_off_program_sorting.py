#!/usr/bin/env python3
"""
Тест сортировки офф-программы по времени начала
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import (
    find_available_off_program_events,
    find_available_off_program_events_before_first_concert,
    find_available_off_program_events_after_last_concert
)
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_off_program_sorting():
    """Тестирует правильность сортировки офф-программы по времени начала"""
    
    try:
        session = next(get_session())
        
        print("🧪 ТЕСТ СОРТИРОВКИ ОФФ-ПРОГРАММЫ ПО ВРЕМЕНИ НАЧАЛА")
        print("=" * 60)
        
        # Получаем все мероприятия офф-программы
        off_program_events = session.exec(select(OffProgram).order_by(OffProgram.event_date)).all()
        print(f"📊 Всего мероприятий офф-программы: {len(off_program_events)}")
        
        # Получаем концерты
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        print(f"🎵 Всего концертов: {len(concerts)}")
        
        if len(concerts) < 2:
            print("❌ Недостаточно концертов для тестирования")
            return
        
        # Тестируем сортировку между концертами
        print(f"\n🔍 ТЕСТ 1: Сортировка между концертами")
        
        # Берем первые два концерта
        concert1 = concerts[0]
        concert2 = concerts[1]
        
        # Создаем структуру данных как в реальном приложении
        current_concert = {
            'concert': {
                'datetime': concert1.datetime,
                'duration': concert1.duration,
                'hall': {'id': concert1.hall_id}
            }
        }
        
        next_concert = {
            'concert': {
                'datetime': concert2.datetime,
                'duration': concert2.duration,
                'hall': {'id': concert2.hall_id}
            }
        }
        
        print(f"Концерт 1: {concert1.datetime.strftime('%H:%M')} - {concert1.name}")
        print(f"Концерт 2: {concert2.datetime.strftime('%H:%M')} - {concert2.name}")
        
        # Ищем офф-программу между концертами
        off_program_between = find_available_off_program_events(session, current_concert, next_concert)
        
        print(f"Найдено мероприятий между концертами: {len(off_program_between)}")
        
        # Проверяем сортировку
        if len(off_program_between) > 1:
            print("Проверяем сортировку по времени начала:")
            for i, event in enumerate(off_program_between):
                print(f"  {i+1}. {event['event_date_display']} - {event['event_name']}")
            
            # Проверяем, что время идет по возрастанию
            is_sorted = True
            for i in range(len(off_program_between) - 1):
                if off_program_between[i]['event_date'] > off_program_between[i+1]['event_date']:
                    is_sorted = False
                    break
            
            if is_sorted:
                print("✅ Сортировка между концертами корректна")
            else:
                print("❌ Сортировка между концертами НЕКОРРЕКТНА")
        else:
            print("ℹ️ Недостаточно мероприятий для проверки сортировки")
        
        # Тестируем сортировку до первого концерта
        print(f"\n🔍 ТЕСТ 2: Сортировка до первого концерта")
        
        first_concert = {
            'concert': {
                'datetime': concert1.datetime,
                'duration': concert1.duration,
                'hall': {'id': concert1.hall_id}
            }
        }
        
        off_program_before = find_available_off_program_events_before_first_concert(session, first_concert)
        
        print(f"Найдено мероприятий до первого концерта: {len(off_program_before)}")
        
        # Проверяем сортировку
        if len(off_program_before) > 1:
            print("Проверяем сортировку по времени начала:")
            for i, event in enumerate(off_program_before):
                print(f"  {i+1}. {event['event_date_display']} - {event['event_name']}")
            
            # Проверяем, что время идет по возрастанию
            is_sorted = True
            for i in range(len(off_program_before) - 1):
                if off_program_before[i]['event_date'] > off_program_before[i+1]['event_date']:
                    is_sorted = False
                    break
            
            if is_sorted:
                print("✅ Сортировка до первого концерта корректна")
            else:
                print("❌ Сортировка до первого концерта НЕКОРРЕКТНА")
        else:
            print("ℹ️ Недостаточно мероприятий для проверки сортировки")
        
        # Тестируем сортировку после последнего концерта
        print(f"\n🔍 ТЕСТ 3: Сортировка после последнего концерта")
        
        last_concert = {
            'concert': {
                'datetime': concert2.datetime,
                'duration': concert2.duration,
                'hall': {'id': concert2.hall_id}
            }
        }
        
        off_program_after = find_available_off_program_events_after_last_concert(session, last_concert)
        
        print(f"Найдено мероприятий после последнего концерта: {len(off_program_after)}")
        
        # Проверяем сортировку
        if len(off_program_after) > 1:
            print("Проверяем сортировку по времени начала:")
            for i, event in enumerate(off_program_after):
                print(f"  {i+1}. {event['event_date_display']} - {event['event_name']}")
            
            # Проверяем, что время идет по возрастанию
            is_sorted = True
            for i in range(len(off_program_after) - 1):
                if off_program_after[i]['event_date'] > off_program_after[i+1]['event_date']:
                    is_sorted = False
                    break
            
            if is_sorted:
                print("✅ Сортировка после последнего концерта корректна")
            else:
                print("❌ Сортировка после последнего концерта НЕКОРРЕКТНА")
        else:
            print("ℹ️ Недостаточно мероприятий для проверки сортировки")
        
        # Дополнительная проверка: показываем все мероприятия офф-программы в хронологическом порядке
        print(f"\n📅 ВСЕ МЕРОПРИЯТИЯ ОФФ-ПРОГРАММЫ (хронологически):")
        for i, event in enumerate(off_program_events[:10], 1):  # Показываем первые 10
            recommend_status = "⭐" if event.recommend else "⬜"
            print(f"  {i:2d}. {event.event_date.strftime('%H:%M')} {recommend_status} {event.event_name}")
        
        print(f"\n✅ ТЕСТ ЗАВЕРШЕН")
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_off_program_sorting() 