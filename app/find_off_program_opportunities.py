#!/usr/bin/env python3
"""
Поиск реальных возможностей посещения офф-программы
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def find_off_program_opportunities():
    """Ищет реальные возможности посещения офф-программы"""
    
    try:
        session = next(get_session())
        
        print("🔍 ПОИСК РЕАЛЬНЫХ ВОЗМОЖНОСТЕЙ ПОСЕЩЕНИЯ ОФФ-ПРОГРАММЫ")
        print("=" * 60)
        
        # Получаем все мероприятия офф-программы
        off_program_events = session.exec(select(OffProgram).order_by(OffProgram.event_date)).all()
        print(f"📊 Всего мероприятий офф-программы: {len(off_program_events)}")
        
        # Показываем временные рамки офф-программы
        if off_program_events:
            first_event = off_program_events[0]
            last_event = off_program_events[-1]
            print(f"📅 Офф-программа: с {first_event.event_date.strftime('%d.%m %H:%M')} до {last_event.event_date.strftime('%d.%m %H:%M')}")
        
        # Получаем концерты, отсортированные по времени
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        print(f"🎵 Всего концертов: {len(concerts)}")
        
        # Показываем временные рамки концертов
        if concerts:
            first_concert = concerts[0]
            last_concert = concerts[-1]
            print(f"📅 Концерты: с {first_concert.datetime.strftime('%d.%m %H:%M')} до {last_concert.datetime.strftime('%d.%m %H:%M')}")
        
        # Ищем пары концертов в период работы офф-программы
        print(f"\n🔍 ПОИСК КОНЦЕРТОВ В ПЕРИОД РАБОТЫ ОФФ-ПРОГРАММЫ:")
        
        # Определяем период работы офф-программы (примерно до 18:00)
        off_program_end_time = datetime(2022, 7, 1, 18, 0)  # 18:00
        
        concert_pairs = []
        
        for i in range(len(concerts) - 1):
            current_concert = concerts[i]
            next_concert = concerts[i + 1]
            
            # Проверяем, что концерты в один день и до 18:00
            if (current_concert.datetime.date() == next_concert.datetime.date() and 
                next_concert.datetime < off_program_end_time):
                
                time_between = (next_concert.datetime - current_concert.datetime).total_seconds() / 60
                
                if time_between > 15:  # Показываем промежутки больше 15 минут
                    concert_pairs.append((current_concert, next_concert, time_between))
        
        print(f"Найдено {len(concert_pairs)} пар концертов с промежутками > 15 минут до 18:00")
        
        # Тестируем все найденные пары
        for i, (current_concert, next_concert, time_between) in enumerate(concert_pairs, 1):
            print(f"\n🎯 ПАРА {i}:")
            print(f"Концерт 1: {current_concert.datetime.strftime('%H:%M')} - {current_concert.name}")
            print(f"Концерт 2: {next_concert.datetime.strftime('%H:%M')} - {next_concert.name}")
            print(f"Промежуток: {time_between:.0f} минут")
            
            # Получаем залы
            current_hall = session.exec(select(Hall).where(Hall.id == current_concert.hall_id)).first()
            next_hall = session.exec(select(Hall).where(Hall.id == next_concert.hall_id)).first()
            
            print(f"Зал 1: {current_hall.name if current_hall else 'Неизвестный'}")
            print(f"Зал 2: {next_hall.name if next_hall else 'Неизвестный'}")
            
            # Вычисляем время окончания первого концерта
            current_end = current_concert.datetime + timedelta(seconds=current_concert.duration.total_seconds())
            print(f"Время окончания концерта 1: {current_end.strftime('%H:%M')}")
            
            # Ищем мероприятия офф-программы в промежутке
            off_program_events_in_gap = session.exec(
                select(OffProgram)
                .where(OffProgram.event_date >= current_end)
                .where(OffProgram.event_date < next_concert.datetime)
                .order_by(OffProgram.event_date)
            ).all()
            
            print(f"Найдено мероприятий офф-программы в промежутке: {len(off_program_events_in_gap)}")
            
            if off_program_events_in_gap:
                for j, event in enumerate(off_program_events_in_gap, 1):
                    print(f"  📋 {j}. {event.event_name} ({event.event_date.strftime('%H:%M')})")
                    print(f"     Зал: {event.hall_name}, Формат: {event.format.value if event.format else 'Не указан'}")
                    print(f"     Продолжительность: {event.event_long}")
            
            # Тестируем нашу функцию
            current_concert_data = {
                'concert': {
                    'id': current_concert.id,
                    'name': current_concert.name,
                    'datetime': current_concert.datetime,
                    'duration': current_concert.duration,
                    'hall': {
                        'id': current_hall.id if current_hall else None,
                        'name': current_hall.name if current_hall else 'Неизвестный зал'
                    } if current_hall else None
                }
            }
            
            next_concert_data = {
                'concert': {
                    'id': next_concert.id,
                    'name': next_concert.name,
                    'datetime': next_concert.datetime,
                    'duration': next_concert.duration,
                    'hall': {
                        'id': next_hall.id if next_hall else None,
                        'name': next_hall.name if next_hall else 'Неизвестный зал'
                    } if next_hall else None
                }
            }
            
            available_events = find_available_off_program_events(
                session, 
                current_concert_data, 
                next_concert_data
            )
            
            print(f"Доступных мероприятий (по функции): {len(available_events)}")
            
            for j, event in enumerate(available_events, 1):
                print(f"  ✅ {j}. {event['event_name']} ({event['event_date_display']})")
                print(f"     Длительность: {event['duration']}, Зал: {event['hall_name']}")
                print(f"     Время переходов: ~{event['total_walk_time']}м, Доступно: {event['available_time']}м")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск поиска возможностей...")
    success = find_off_program_opportunities()
    if success:
        print("\n✅ Поиск завершен успешно!")
    else:
        print("\n💥 Поиск завершен с ошибками!")
        sys.exit(1) 