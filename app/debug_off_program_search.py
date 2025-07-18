#!/usr/bin/env python3
"""
Детальный отладчик поиска мероприятий офф-программы
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def debug_off_program_search():
    """Детально анализирует поиск мероприятий офф-программы"""
    
    try:
        session = next(get_session())
        
        print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ПОИСКА МЕРОПРИЯТИЙ ОФФ-ПРОГРАММЫ")
        print("=" * 60)
        
        # Получаем все мероприятия офф-программы
        off_program_events = session.exec(select(OffProgram).order_by(OffProgram.event_date)).all()
        print(f"📊 Всего мероприятий офф-программы: {len(off_program_events)}")
        
        print("\n📅 РАСПИСАНИЕ МЕРОПРИЯТИЙ ОФФ-ПРОГРАММЫ:")
        for i, event in enumerate(off_program_events[:10], 1):  # Показываем первые 10
            print(f"  {i:2d}. {event.event_date.strftime('%d.%m %H:%M')} - {event.event_name}")
            print(f"       Зал: {event.hall_name}, Формат: {event.format.value if event.format else 'Не указан'}")
        
        # Получаем концерты, отсортированные по времени
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        print(f"\n🎵 Всего концертов: {len(concerts)}")
        
        print("\n📅 РАСПИСАНИЕ КОНЦЕРТОВ:")
        for i, concert in enumerate(concerts[:10], 1):  # Показываем первые 10
            hall = session.exec(select(Hall).where(Hall.id == concert.hall_id)).first()
            hall_name = hall.name if hall else "Неизвестный зал"
            print(f"  {i:2d}. {concert.datetime.strftime('%d.%m %H:%M')} - {concert.name}")
            print(f"       Зал: {hall_name}, Длительность: {concert.duration}")
        
        # Ищем пары концертов с промежутками
        print(f"\n🔍 ПОИСК КОНЦЕРТОВ С ПРОМЕЖУТКАМИ:")
        concert_pairs = []
        
        for i in range(len(concerts) - 1):
            current_concert = concerts[i]
            next_concert = concerts[i + 1]
            
            # Проверяем, что концерты в один день
            if current_concert.datetime.date() == next_concert.datetime.date():
                time_between = (next_concert.datetime - current_concert.datetime).total_seconds() / 60
                
                if time_between > 30:  # Показываем только если промежуток больше 30 минут
                    concert_pairs.append((current_concert, next_concert, time_between))
        
        print(f"Найдено {len(concert_pairs)} пар концертов с промежутками > 30 минут")
        
        # Тестируем первые 3 пары
        for i, (current_concert, next_concert, time_between) in enumerate(concert_pairs[:3], 1):
            print(f"\n🎯 ТЕСТ ПАРЫ {i}:")
            print(f"Концерт 1: {current_concert.datetime.strftime('%H:%M')} - {current_concert.name}")
            print(f"Концерт 2: {next_concert.datetime.strftime('%H:%M')} - {next_concert.name}")
            print(f"Промежуток: {time_between:.0f} минут")
            
            # Получаем залы
            current_hall = session.exec(select(Hall).where(Hall.id == current_concert.hall_id)).first()
            next_hall = session.exec(select(Hall).where(Hall.id == next_concert.hall_id)).first()
            
            # Создаем тестовые данные
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
            
            # Ищем доступные мероприятия
            available_events = find_available_off_program_events(
                session, 
                current_concert_data, 
                next_concert_data
            )
            
            print(f"Найдено доступных мероприятий: {len(available_events)}")
            
            for j, event in enumerate(available_events, 1):
                print(f"  {j}. {event['event_name']} ({event['event_date_display']})")
                print(f"     Длительность: {event['duration']}, Зал: {event['hall_name']}")
                print(f"     Время переходов: ~{event['total_walk_time']}м, Доступно: {event['available_time']}м")
        
        # Показываем все мероприятия офф-программы с их временными рамками
        print(f"\n📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О МЕРОПРИЯТИЯХ ОФФ-ПРОГРАММЫ:")
        for i, event in enumerate(off_program_events, 1):
            # Вычисляем продолжительность
            duration_str = "30м"  # По умолчанию
            if event.event_long:
                try:
                    time_parts = str(event.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        if hours > 0 and minutes > 0:
                            duration_str = f"{hours}ч {minutes}м"
                        elif hours > 0:
                            duration_str = f"{hours}ч"
                        else:
                            duration_str = f"{minutes}м"
                except:
                    duration_str = "30м"
            
            print(f"  {i:2d}. {event.event_date.strftime('%d.%m %H:%M')} - {event.event_name}")
            print(f"       Длительность: {duration_str}, Зал: {event.hall_name}")
            print(f"       Формат: {event.format.value if event.format else 'Не указан'}")
            print(f"       Рекомендуется: {'Да' if event.recommend else 'Нет'}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отладке: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск детального отладчика...")
    success = debug_off_program_search()
    if success:
        print("\n✅ Отладка завершена успешно!")
    else:
        print("\n💥 Отладка завершена с ошибками!")
        sys.exit(1) 