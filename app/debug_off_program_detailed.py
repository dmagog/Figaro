#!/usr/bin/env python3
"""
Детальный отладчик с анализом причин недоступности мероприятий офф-программы
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def debug_off_program_detailed():
    """Детально анализирует, почему мероприятия офф-программы недоступны"""
    
    try:
        session = next(get_session())
        
        print("🔍 ДЕТАЛЬНЫЙ АНАЛИЗ ДОСТУПНОСТИ МЕРОПРИЯТИЙ ОФФ-ПРОГРАММЫ")
        print("=" * 70)
        
        # Получаем концерты, отсортированные по времени
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        
        # Ищем пары концертов с промежутками
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
        
        # Тестируем первые 3 пары с детальным анализом
        for i, (current_concert, next_concert, time_between) in enumerate(concert_pairs[:3], 1):
            print(f"\n🎯 ДЕТАЛЬНЫЙ АНАЛИЗ ПАРЫ {i}:")
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
            off_program_events = session.exec(
                select(OffProgram)
                .where(OffProgram.event_date >= current_end)
                .where(OffProgram.event_date < next_concert.datetime)
                .order_by(OffProgram.event_date)
            ).all()
            
            print(f"Найдено мероприятий офф-программы в промежутке: {len(off_program_events)}")
            
            for j, event in enumerate(off_program_events, 1):
                print(f"\n  📋 Мероприятие {j}: {event.event_name}")
                print(f"     Время начала: {event.event_date.strftime('%H:%M')}")
                print(f"     Зал: {event.hall_name}")
                print(f"     Продолжительность (raw): {event.event_long}")
                
                # Вычисляем продолжительность мероприятия
                event_duration = timedelta()
                if event.event_long:
                    try:
                        time_parts = str(event.event_long).split(':')
                        if len(time_parts) >= 2:
                            hours = int(time_parts[0])
                            minutes = int(time_parts[1])
                            event_duration = timedelta(hours=hours, minutes=minutes)
                    except:
                        event_duration = timedelta(minutes=30)
                
                print(f"     Продолжительность (parsed): {event_duration}")
                
                # Вычисляем время окончания мероприятия
                event_end = event.event_date + event_duration
                print(f"     Время окончания: {event_end.strftime('%H:%M')}")
                
                # Проверяем, помещается ли мероприятие
                if event_end <= next_concert.datetime:
                    print(f"     ✅ Мероприятие помещается во временной промежуток")
                    
                    # Рассчитываем время переходов
                    walk_time_to_event = 0
                    walk_time_from_event = 0
                    
                    if event.hall_name.lower() == 'инфоцентр':
                        if current_hall and 'инфоцентр' in current_hall.name.lower():
                            walk_time_to_event = 0
                        else:
                            walk_time_to_event = 10
                        
                        if next_hall and 'инфоцентр' in next_hall.name.lower():
                            walk_time_from_event = 0
                        else:
                            walk_time_from_event = 10
                    else:
                        walk_time_to_event = 5
                        walk_time_from_event = 5
                    
                    total_walk_time = walk_time_to_event + walk_time_from_event
                    available_time = (next_concert.datetime - current_end).total_seconds() / 60
                    event_duration_minutes = event_duration.total_seconds() / 60
                    
                    print(f"     Время перехода к мероприятию: {walk_time_to_event}м")
                    print(f"     Время перехода от мероприятия: {walk_time_from_event}м")
                    print(f"     Общее время переходов: {total_walk_time}м")
                    print(f"     Доступное время: {available_time:.0f}м")
                    print(f"     Длительность мероприятия: {event_duration_minutes:.0f}м")
                    print(f"     Требуемое время: {total_walk_time + event_duration_minutes:.0f}м")
                    
                    if total_walk_time + event_duration_minutes <= available_time:
                        print(f"     ✅ Мероприятие доступно!")
                    else:
                        print(f"     ❌ Недостаточно времени: нужно {total_walk_time + event_duration_minutes:.0f}м, есть {available_time:.0f}м")
                else:
                    print(f"     ❌ Мероприятие не помещается во временной промежуток")
                    print(f"     Мероприятие заканчивается в {event_end.strftime('%H:%M')}, а следующий концерт начинается в {next_concert.datetime.strftime('%H:%M')}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отладке: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск детального отладчика...")
    success = debug_off_program_detailed()
    if success:
        print("\n✅ Отладка завершена успешно!")
    else:
        print("\n💥 Отладка завершена с ошибками!")
        sys.exit(1) 