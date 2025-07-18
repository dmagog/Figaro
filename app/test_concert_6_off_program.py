#!/usr/bin/env python3
"""
Тест для проверки офф-программы перед концертом 6
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events_before_first_concert
from models import Concert
from sqlalchemy import select

def test_concert_6_off_program():
    """Тест поиска офф-программы перед концертом 6"""
    print("🧪 Тестируем поиск офф-программы перед концертом 6...")
    
    session = next(get_session())
    
    try:
        # Получаем концерт 6
        concert_6 = session.exec(
            select(Concert).where(Concert.id == 6)
        ).first()
        
        if not concert_6:
            print("❌ Концерт 6 не найден в базе данных")
            return False
        
        # Извлекаем данные из Row объекта если нужно
        if hasattr(concert_6, '_mapping'):
            concert_data = concert_6._mapping['Concert']
        else:
            concert_data = concert_6
        
        print(f"📅 Концерт 6: {concert_data.name}")
        print(f"🕐 Время: {concert_data.datetime.strftime('%H:%M')}")
        print(f"📍 Зал ID: {concert_data.hall_id}")
        
        # Получаем зал
        from models import Hall
        hall = session.exec(
            select(Hall).where(Hall.id == concert_data.hall_id)
        ).first()
        
        if hall:
            if hasattr(hall, '_mapping'):
                hall_data = hall._mapping['Hall']
            else:
                hall_data = hall
            print(f"🏛️ Зал: {hall_data.name}")
        
        # Создаем концерт в формате словаря для функции
        concert_dict = {
            'concert': {
                'datetime': concert_data.datetime,
                'hall': {'id': concert_data.hall_id}
            }
        }
        
        # Тестируем функцию поиска офф-программы
        events = find_available_off_program_events_before_first_concert(session, concert_dict)
        
        print(f"\n✅ Найдено мероприятий до концерта 6: {len(events)}")
        
        if events:
            print("\n📋 Мероприятия до концерта 6:")
            for event in events:
                print(f"   • {event['event_date_display']} - {event['event_name']}")
                print(f"     📍 {event['hall_name']} • {event['format']} • {event['duration']}")
                print(f"     🚶🏼‍➡️ Переход к концерту: ~{event['walk_time_to_concert']} мин")
                print(f"     🕐 Доступное время: {event['available_time']} мин")
                if event['description']:
                    print(f"     📝 {event['description']}")
                print()
        else:
            print("   ❌ Мероприятия не найдены")
            
            # Проверим, есть ли вообще мероприятия офф-программы в этот день
            from models import OffProgram
            from datetime import timedelta
            
            day_start = concert_data.datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_events = session.exec(
                select(OffProgram)
                .where(OffProgram.event_date >= day_start)
                .where(OffProgram.event_date < day_end)
                .order_by(OffProgram.event_date)
            ).all()
            
            print(f"\n🔍 Всего мероприятий офф-программы в этот день: {len(day_events)}")
            
            if day_events:
                print("📋 Все мероприятия дня:")
                for event in day_events:
                    if hasattr(event, '_mapping'):
                        event_data = event._mapping['OffProgram']
                    else:
                        event_data = event
                    print(f"   • {event_data.event_date.strftime('%H:%M')} - {event_data.event_name} ({event_data.hall_name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Запуск теста офф-программы перед концертом 6")
    print("=" * 60)
    
    if test_concert_6_off_program():
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n⚠️ Тест не прошел") 