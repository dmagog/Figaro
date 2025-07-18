#!/usr/bin/env python3
"""
Тест для конкретных концертов 1 и 15
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_specific_concerts():
    """Тестирует функцию на конкретных концертах 1 и 15"""
    
    try:
        session = next(get_session())
        
        print("🎯 ТЕСТ КОНКРЕТНЫХ КОНЦЕРТОВ 1 И 15")
        print("=" * 50)
        
        # Получаем концерты
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        
        if len(concerts) < 15:
            print(f"❌ Недостаточно концертов: {len(concerts)}")
            return False
        
        # Берем концерты 1 и 15 (индексы 0 и 14)
        concert1 = concerts[0]
        concert15 = concerts[14]
        
        print(f"Концерт 1: {concert1.datetime.strftime('%d.%m %H:%M')} - {concert1.name}")
        print(f"Концерт 15: {concert15.datetime.strftime('%d.%m %H:%M')} - {concert15.name}")
        
        # Получаем залы
        hall1 = session.exec(select(Hall).where(Hall.id == concert1.hall_id)).first()
        hall15 = session.exec(select(Hall).where(Hall.id == concert15.hall_id)).first()
        
        print(f"Зал концерта 1: {hall1.name if hall1 else 'Неизвестный'}")
        print(f"Зал концерта 15: {hall15.name if hall15 else 'Неизвестный'}")
        
        # Вычисляем промежуток
        time_between = (concert15.datetime - concert1.datetime).total_seconds() / 60
        print(f"Промежуток между концертами: {time_between:.0f} минут")
        
        # Вычисляем время окончания первого концерта
        concert1_end = concert1.datetime + timedelta(seconds=concert1.duration.total_seconds())
        print(f"Время окончания концерта 1: {concert1_end.strftime('%H:%M')}")
        
        # Ищем мероприятия офф-программы между концертами
        off_program_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= concert1_end)
            .where(OffProgram.event_date < concert15.datetime)
            .order_by(OffProgram.event_date)
        ).all()
        
        print(f"\n📋 Найдено {len(off_program_events)} мероприятий офф-программы между концертами:")
        
        for i, event in enumerate(off_program_events, 1):
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
        
        # Тестируем нашу функцию
        print(f"\n🧪 ТЕСТИРУЕМ НАШУ ФУНКЦИЮ:")
        
        current_concert_data = {
            'concert': {
                'id': concert1.id,
                'name': concert1.name,
                'datetime': concert1.datetime,
                'duration': concert1.duration,
                'hall': {
                    'id': hall1.id if hall1 else None,
                    'name': hall1.name if hall1 else 'Неизвестный зал'
                } if hall1 else None
            }
        }
        
        next_concert_data = {
            'concert': {
                'id': concert15.id,
                'name': concert15.name,
                'datetime': concert15.datetime,
                'duration': concert15.duration,
                'hall': {
                    'id': hall15.id if hall15 else None,
                    'name': hall15.name if hall15 else 'Неизвестный зал'
                } if hall15 else None
            }
        }
        
        available_events = find_available_off_program_events(
            session, 
            current_concert_data, 
            next_concert_data
        )
        
        print(f"Доступных мероприятий (по функции): {len(available_events)}")
        
        for event in available_events:
            print(f"  ✅ {event['event_name']} ({event['event_date_display']})")
            print(f"     Длительность: {event['duration']}, Зал: {event['hall_name']}")
            print(f"     Время переходов: ~{event['total_walk_time']}м, Доступно: {event['available_time']}м")
            print(f"     Формат: {event['format']}")
            print(f"     Рекомендуется: {'Да' if event['recommend'] else 'Нет'}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск теста конкретных концертов...")
    success = test_specific_concerts()
    if success:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n💥 Тест завершен с ошибками!")
        sys.exit(1) 