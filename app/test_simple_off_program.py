#!/usr/bin/env python3
"""
Простой тест для проверки работы с реальными данными
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from models import Concert, Hall, OffProgram
from sqlalchemy import select
from datetime import datetime, timedelta

def test_real_data():
    """Тест с реальными данными из базы"""
    print("🧪 Тестируем с реальными данными...")
    
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
        
        # Извлекаем данные из Row объектов
        if hasattr(first_concert, '_mapping'):
            first_concert_data = first_concert._mapping['Concert']
        else:
            first_concert_data = first_concert
            
        if hasattr(last_concert, '_mapping'):
            last_concert_data = last_concert._mapping['Concert']
        else:
            last_concert_data = last_concert
        
        print(f"📅 Первый концерт: {first_concert_data.name} в {first_concert_data.datetime.strftime('%H:%M')}")
        print(f"📅 Последний концерт: {last_concert_data.name} в {last_concert_data.datetime.strftime('%H:%M')}")
        
        # Проверяем, есть ли мероприятия офф-программы в базе
        off_program_count = session.exec(select(OffProgram)).all()
        print(f"📊 Всего мероприятий офф-программы в базе: {len(off_program_count)}")
        
        if off_program_count:
            print("\n📋 Примеры мероприятий офф-программы:")
            for event in off_program_count[:5]:  # Показываем первые 5
                print(f"   • {event.event_date.strftime('%H:%M')} - {event.event_name} ({event.hall_name})")
        
        # Проверяем временные окна
        search_start_before = first_concert_data.datetime - timedelta(hours=2)
        search_end_after = last_concert_data.datetime + timedelta(hours=2)
        
        print(f"\n🔍 Временные окна поиска:")
        print(f"   До первого концерта: {search_start_before.strftime('%H:%M')} - {first_concert.datetime.strftime('%H:%M')}")
        print(f"   После последнего концерта: {last_concert.datetime.strftime('%H:%M')} - {search_end_after.strftime('%H:%M')}")
        
        # Ищем мероприятия в этих окнах
        before_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= search_start_before)
            .where(OffProgram.event_date < first_concert_data.datetime)
        ).all()
        
        after_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date > last_concert_data.datetime)
            .where(OffProgram.event_date <= search_end_after)
        ).all()
        
        print(f"\n✅ Найдено мероприятий до первого концерта: {len(before_events)}")
        print(f"✅ Найдено мероприятий после последнего концерта: {len(after_events)}")
        
        if before_events:
            print("\n📋 Мероприятия до первого концерта:")
            for event in before_events:
                print(f"   • {event.event_date.strftime('%H:%M')} - {event.event_name} ({event.hall_name})")
        
        if after_events:
            print("\n📋 Мероприятия после последнего концерта:")
            for event in after_events:
                print(f"   • {event.event_date.strftime('%H:%M')} - {event.event_name} ({event.hall_name})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте с реальными данными: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Запуск простого теста с реальными данными")
    print("=" * 60)
    
    if test_real_data():
        print("\n🎉 Тест прошел успешно!")
    else:
        print("\n⚠️ Тест не прошел") 