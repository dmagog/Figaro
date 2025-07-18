#!/usr/bin/env python3
"""
Тестирование функции поиска офф-программы с реальными данными о переходах
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall, HallTransition
from datetime import datetime, timedelta
from sqlmodel import select

def test_off_program_with_real_transitions():
    """Тестирует функцию поиска офф-программы с реальными данными о переходах"""
    
    print("🔍 ТЕСТИРОВАНИЕ ОФФ-ПРОГРАММЫ С РЕАЛЬНЫМИ ПЕРЕХОДАМИ")
    print("=" * 60)
    
    try:
        session = next(get_session())
        
        # Получаем концерты 1 и 15 для тестирования
        concert1 = session.exec(select(Concert).where(Concert.id == 1)).first()
        concert15 = session.exec(select(Concert).where(Concert.id == 15)).first()
        
        if not concert1 or not concert15:
            print("❌ Концерты 1 или 15 не найдены")
            return False
        
        print(f"✅ Концерт 1: {concert1.datetime.strftime('%H:%M')} - {concert1.name}")
        print(f"✅ Концерт 15: {concert15.datetime.strftime('%H:%M')} - {concert15.name}")
        
        # Получаем залы
        hall1 = session.exec(select(Hall).where(Hall.id == concert1.hall_id)).first()
        hall15 = session.exec(select(Hall).where(Hall.id == concert15.hall_id)).first()
        
        print(f"   Зал 1: {hall1.name if hall1 else 'Неизвестный'}")
        print(f"   Зал 15: {hall15.name if hall15 else 'Неизвестный'}")
        
        # Проверяем переход между залами
        if hall1 and hall15:
            transition = session.exec(
                select(HallTransition)
                .where(HallTransition.from_hall_id == hall1.id)
                .where(HallTransition.to_hall_id == hall15.id)
            ).first()
            
            if not transition:
                transition = session.exec(
                    select(HallTransition)
                    .where(HallTransition.from_hall_id == hall15.id)
                    .where(HallTransition.to_hall_id == hall1.id)
                ).first()
            
            if transition:
                print(f"   Переход между залами: {transition.transition_time} мин")
            else:
                print(f"   Переход между залами: не найден")
        
        # Вычисляем время окончания первого концерта
        concert1_end = concert1.datetime + timedelta(seconds=concert1.duration.total_seconds())
        print(f"   Время окончания концерта 1: {concert1_end.strftime('%H:%M')}")
        
        # Ищем мероприятия офф-программы между концертами
        off_program_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= concert1_end)
            .where(OffProgram.event_date < concert15.datetime)
            .order_by(OffProgram.event_date)
        ).all()
        
        print(f"\n📋 Найдено {len(off_program_events)} мероприятий офф-программы между концертами:")
        
        for i, event in enumerate(off_program_events, 1):
            # Ищем зал мероприятия
            event_hall = session.exec(
                select(Hall).where(Hall.name.ilike(f'%{event.hall_name}%'))
            ).first()
            
            print(f"  {i:2d}. {event.event_date.strftime('%H:%M')} - {event.event_name}")
            print(f"       Зал: {event.hall_name} (ID: {event_hall.id if event_hall else 'не найден'})")
            print(f"       Длительность: {event.event_long}")
        
        # Подготавливаем данные для функции
        current_concert_data = {
            'concert': {
                'datetime': concert1.datetime,
                'duration': concert1.duration,
                'hall': {'id': hall1.id} if hall1 else {}
            }
        }
        
        next_concert_data = {
            'concert': {
                'datetime': concert15.datetime,
                'hall': {'id': hall15.id} if hall15 else {}
            }
        }
        
        # Тестируем нашу функцию
        print(f"\n🧪 ТЕСТИРУЕМ ФУНКЦИЮ С РЕАЛЬНЫМИ ПЕРЕХОДАМИ:")
        available_events = find_available_off_program_events(session, current_concert_data, next_concert_data)
        
        print(f"✅ Функция вернула {len(available_events)} доступных мероприятий:")
        
        for i, event in enumerate(available_events, 1):
            print(f"  {i:2d}. {event['event_name']}")
            print(f"       Время: {event['event_date_display']}, Длительность: {event['duration']}")
            print(f"       Зал: {event['hall_name']}")
            print(f"       Переход к мероприятию: {event['walk_time_to_event']} мин")
            print(f"       Переход от мероприятия: {event['walk_time_from_event']} мин")
            print(f"       Общее время переходов: {event['total_walk_time']} мин")
            print(f"       Доступное время: {event['available_time']} мин")
            print(f"       Длительность мероприятия: {event['event_duration_minutes']} мин")
        
        # Показываем диагностическую информацию о залах офф-программы
        print(f"\n🔍 ДИАГНОСТИКА ЗАЛОВ ОФФ-ПРОГРАММЫ:")
        for event in off_program_events:
            event_hall = session.exec(
                select(Hall).where(Hall.name.ilike(f'%{event.hall_name}%'))
            ).first()
            
            if event_hall:
                print(f"   ✅ '{event.hall_name}' найден как зал ID={event_hall.id}: '{event_hall.name}'")
            else:
                print(f"   ❌ '{event.hall_name}' НЕ НАЙДЕН в базе залов")
        
        # Показываем все залы для сравнения
        print(f"\n🏛️ ВСЕ ЗАЛЫ В БАЗЕ ДАННЫХ:")
        all_halls = session.exec(select(Hall)).all()
        for hall in all_halls:
            print(f"   ID={hall.id}: '{hall.name}'")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_off_program_with_real_transitions() 