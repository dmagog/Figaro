#!/usr/bin/env python3
"""
Скрипт для отладки данных офф-программы после последнего концерта
"""

from database.database import get_session
from routes.user import find_available_off_program_events_after_last_concert
from models import Concert, Hall, OffProgram
from sqlmodel import select
from datetime import datetime, timedelta

def debug_after_concert():
    """Отлаживает данные офф-программы после последнего концерта"""
    session = next(get_session())
    
    try:
        # Находим концерт для тестирования
        concert = session.exec(select(Concert).limit(1)).first()
        if not concert:
            print("❌ Концерты не найдены")
            return
        
        print(f"🎵 Тестируем концерт: {concert.name}")
        print(f"   📅 Дата: {concert.datetime}")
        print(f"   ⏱️ Длительность: {concert.duration}")
        
        # Получаем зал концерта
        hall = session.exec(select(Hall).where(Hall.id == concert.hall_id)).first()
        print(f"   🏛️ Зал: {hall.name if hall else 'Не найден'}")
        
        # Создаем словарь концерта в нужном формате
        concert_dict = {
            'concert': {
                'datetime': concert.datetime,
                'duration': concert.duration,
                'hall': {'id': concert.hall_id}
            }
        }
        
        # Тестируем функцию
        events = find_available_off_program_events_after_last_concert(session, concert_dict)
        
        print(f"\n📊 Найдено мероприятий после концерта: {len(events)}")
        
        for i, event in enumerate(events):
            print(f"\n🎯 Мероприятие {i+1}:")
            print(f"   📅 Время: {event['event_date_display']}")
            print(f"   🎯 Название: {event['event_name']}")
            print(f"   ⏱️ Длительность: {event['duration']}")
            print(f"   📍 Зал: {event['hall_name']}")
            print(f"   🚶🏼‍➡️ Время перехода: {event['walk_time_from_concert']} мин")
            print(f"   🕐 Доступное время: {event['available_time']} мин")
            print(f"   🏷️ Тип: {event['type']}")
            
            # Проверяем, что именно возвращается
            print(f"   🔍 walk_time_from_concert тип: {type(event['walk_time_from_concert'])}")
            print(f"   🔍 walk_time_from_concert значение: {repr(event['walk_time_from_concert'])}")
        
        if not events:
            print("\n🔍 Проверяем доступные мероприятия офф-программы...")
            
            # Вычисляем время окончания концерта
            if hasattr(concert.duration, 'total_seconds'):
                concert_end = concert.datetime + timedelta(seconds=concert.duration.total_seconds())
            else:
                try:
                    time_parts = str(concert.duration).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        concert_end = concert.datetime + timedelta(hours=hours, minutes=minutes)
                    else:
                        concert_end = concert.datetime + timedelta(hours=1)
                except:
                    concert_end = concert.datetime + timedelta(hours=1)
            
            print(f"   ⏰ Время окончания концерта: {concert_end}")
            
            # Ищем мероприятия после концерта
            search_end = datetime.combine(concert_end.date(), datetime.max.time().replace(hour=22, minute=0))
            print(f"   🔍 Поиск до: {search_end}")
            
            off_program_events = session.exec(
                select(OffProgram)
                .where(OffProgram.event_date >= concert_end)
                .where(OffProgram.event_date <= search_end)
                .order_by(OffProgram.event_date)
            ).all()
            
            print(f"   📊 Найдено мероприятий в базе: {len(off_program_events)}")
            
            for event in off_program_events[:3]:  # Показываем первые 3
                print(f"     - {event.event_name} в {event.event_date.strftime('%H:%M')} (зал: {event.hall_name})")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    debug_after_concert() 