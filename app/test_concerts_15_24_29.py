#!/usr/bin/env python3
"""
Анализ конкретного случая: концерты 15, 24 и 29
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall, HallTransition
from datetime import datetime, timedelta
from sqlmodel import select

def test_concerts_15_24_29():
    """Анализирует конкретный случай с концертами 15, 24 и 29"""
    
    print("🔍 АНАЛИЗ КОНКРЕТНОГО СЛУЧАЯ: КОНЦЕРТЫ 15, 24 И 29")
    print("=" * 60)
    
    try:
        session = next(get_session())
        
        # Получаем концерты 15, 24 и 29
        concert15 = session.exec(select(Concert).where(Concert.id == 15)).first()
        concert24 = session.exec(select(Concert).where(Concert.id == 24)).first()
        concert29 = session.exec(select(Concert).where(Concert.id == 29)).first()
        
        if not concert15 or not concert24 or not concert29:
            print("❌ Один из концертов 15, 24 или 29 не найден")
            return False
        
        print(f"✅ Концерт 15: {concert15.datetime.strftime('%H:%M')} - {concert15.name}")
        print(f"✅ Концерт 24: {concert24.datetime.strftime('%H:%M')} - {concert24.name}")
        print(f"✅ Концерт 29: {concert29.datetime.strftime('%H:%M')} - {concert29.name}")
        
        # Получаем залы
        hall15 = session.exec(select(Hall).where(Hall.id == concert15.hall_id)).first()
        hall24 = session.exec(select(Hall).where(Hall.id == concert24.hall_id)).first()
        hall29 = session.exec(select(Hall).where(Hall.id == concert29.hall_id)).first()
        
        print(f"\n🏛️ ЗАЛЫ:")
        print(f"   Концерт 15: {hall15.name if hall15 else 'Неизвестный'}")
        print(f"   Концерт 24: {hall24.name if hall24 else 'Неизвестный'}")
        print(f"   Концерт 29: {hall29.name if hall29 else 'Неизвестный'}")
        
        # Вычисляем время окончания концертов
        concert15_end = concert15.datetime + timedelta(seconds=concert15.duration.total_seconds())
        concert24_end = concert24.datetime + timedelta(seconds=concert24.duration.total_seconds())
        
        print(f"\n⏰ ВРЕМЕННЫЕ ПРОМЕЖУТКИ:")
        print(f"   Концерт 15 заканчивается: {concert15_end.strftime('%H:%M')}")
        print(f"   Концерт 24 начинается: {concert24.datetime.strftime('%H:%M')}")
        print(f"   Концерт 24 заканчивается: {concert24_end.strftime('%H:%M')}")
        print(f"   Концерт 29 начинается: {concert29.datetime.strftime('%H:%M')}")
        
        # Рассчитываем промежутки
        gap_15_24 = (concert24.datetime - concert15_end).total_seconds() / 60
        gap_24_29 = (concert29.datetime - concert24_end).total_seconds() / 60
        
        print(f"   Промежуток 15→24: {gap_15_24:.0f} минут")
        print(f"   Промежуток 24→29: {gap_24_29:.0f} минут")
        
        # Ищем все мероприятия офф-программы в промежутке 15→24
        print(f"\n📋 МЕРОПРИЯТИЯ ОФФ-ПРОГРАММЫ МЕЖДУ 15 И 24:")
        off_program_events_15_24 = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= concert15_end)
            .where(OffProgram.event_date < concert24.datetime)
            .order_by(OffProgram.event_date)
        ).all()
        
        print(f"Найдено {len(off_program_events_15_24)} мероприятий:")
        
        for i, event in enumerate(off_program_events_15_24, 1):
            # Вычисляем продолжительность
            duration_minutes = 0
            if event.event_long:
                try:
                    time_parts = str(event.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        duration_minutes = hours * 60 + minutes
                except:
                    duration_minutes = 30
            
            print(f"  {i:2d}. {event.event_date.strftime('%H:%M')} - {event.event_name}")
            print(f"       Длительность: {duration_minutes}м, Зал: {event.hall_name}")
            print(f"       Формат: {event.format.value if event.format else 'Не указан'}")
        
        # Ищем все мероприятия офф-программы в промежутке 24→29
        print(f"\n📋 МЕРОПРИЯТИЯ ОФФ-ПРОГРАММЫ МЕЖДУ 24 И 29:")
        off_program_events_24_29 = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= concert24_end)
            .where(OffProgram.event_date < concert29.datetime)
            .order_by(OffProgram.event_date)
        ).all()
        
        print(f"Найдено {len(off_program_events_24_29)} мероприятий:")
        
        for i, event in enumerate(off_program_events_24_29, 1):
            # Вычисляем продолжительность
            duration_minutes = 0
            if event.event_long:
                try:
                    time_parts = str(event.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        duration_minutes = hours * 60 + minutes
                except:
                    duration_minutes = 30
            
            print(f"  {i:2d}. {event.event_date.strftime('%H:%M')} - {event.event_name}")
            print(f"       Длительность: {duration_minutes}м, Зал: {event.hall_name}")
            print(f"       Формат: {event.format.value if event.format else 'Не указан'}")
        
        # Тестируем нашу функцию для промежутка 15→24
        print(f"\n🧪 ТЕСТИРУЕМ ФУНКЦИЮ ДЛЯ ПРОМЕЖУТКА 15→24:")
        
        current_concert_data = {
            'concert': {
                'datetime': concert15.datetime,
                'duration': concert15.duration,
                'hall': {'id': hall15.id} if hall15 else {}
            }
        }
        
        next_concert_data = {
            'concert': {
                'datetime': concert24.datetime,
                'hall': {'id': hall24.id} if hall24 else {}
            }
        }
        
        available_events_15_24 = find_available_off_program_events(session, current_concert_data, next_concert_data)
        
        print(f"✅ Функция вернула {len(available_events_15_24)} доступных мероприятий:")
        
        for i, event in enumerate(available_events_15_24, 1):
            print(f"  {i:2d}. {event['event_name']}")
            print(f"       Время: {event['event_date_display']}, Длительность: {event['duration']}")
            print(f"       Зал: {event['hall_name']}")
            print(f"       Переход к мероприятию: {event['walk_time_to_event']} мин")
            print(f"       Переход от мероприятия: {event['walk_time_from_event']} мин")
            print(f"       Общее время переходов: {event['total_walk_time']} мин")
            print(f"       Доступное время: {event['available_time']} мин")
            print(f"       Длительность мероприятия: {event['event_duration_minutes']} мин")
        
        # Тестируем нашу функцию для промежутка 24→29
        print(f"\n🧪 ТЕСТИРУЕМ ФУНКЦИЮ ДЛЯ ПРОМЕЖУТКА 24→29:")
        
        current_concert_data = {
            'concert': {
                'datetime': concert24.datetime,
                'duration': concert24.duration,
                'hall': {'id': hall24.id} if hall24 else {}
            }
        }
        
        next_concert_data = {
            'concert': {
                'datetime': concert29.datetime,
                'hall': {'id': hall29.id} if hall29 else {}
            }
        }
        
        available_events_24_29 = find_available_off_program_events(session, current_concert_data, next_concert_data)
        
        print(f"✅ Функция вернула {len(available_events_24_29)} доступных мероприятий:")
        
        for i, event in enumerate(available_events_24_29, 1):
            print(f"  {i:2d}. {event['event_name']}")
            print(f"       Время: {event['event_date_display']}, Длительность: {event['duration']}")
            print(f"       Зал: {event['hall_name']}")
            print(f"       Переход к мероприятию: {event['walk_time_to_event']} мин")
            print(f"       Переход от мероприятия: {event['walk_time_from_event']} мин")
            print(f"       Общее время переходов: {event['total_walk_time']} мин")
            print(f"       Доступное время: {event['available_time']} мин")
            print(f"       Длительность мероприятия: {event['event_duration_minutes']} мин")
        
        # Диагностика залов офф-программы
        print(f"\n🔍 ДИАГНОСТИКА ЗАЛОВ ОФФ-ПРОГРАММЫ:")
        all_off_program_events = off_program_events_15_24 + off_program_events_24_29
        unique_halls = set(event.hall_name for event in all_off_program_events)
        
        for hall_name in unique_halls:
            event_hall = session.exec(
                select(Hall).where(Hall.name.ilike(f'%{hall_name}%'))
            ).first()
            
            if event_hall:
                print(f"   ✅ '{hall_name}' найден как зал ID={event_hall.id}: '{event_hall.name}'")
            else:
                print(f"   ❌ '{hall_name}' НЕ НАЙДЕН в базе залов")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_concerts_15_24_29() 