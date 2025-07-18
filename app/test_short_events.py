#!/usr/bin/env python3
"""
Тест для поиска мероприятий офф-программы с короткой продолжительностью
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_short_events():
    """Тестирует поиск мероприятий с короткой продолжительностью"""
    
    try:
        session = next(get_session())
        
        print("🔍 ПОИСК МЕРОПРИЯТИЙ С КОРОТКОЙ ПРОДОЛЖИТЕЛЬНОСТЬЮ")
        print("=" * 60)
        
        # Получаем все мероприятия офф-программы
        off_program_events = session.exec(select(OffProgram).order_by(OffProgram.event_date)).all()
        
        # Анализируем продолжительность мероприятий
        short_events = []
        for event in off_program_events:
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
            
            if duration_minutes <= 60:  # Мероприятия до 1 часа
                short_events.append((event, duration_minutes))
        
        print(f"📊 Найдено {len(short_events)} мероприятий с продолжительностью до 1 часа:")
        
        for i, (event, duration) in enumerate(short_events, 1):
            print(f"  {i:2d}. {event.event_date.strftime('%d.%m %H:%M')} - {event.event_name}")
            print(f"       Длительность: {duration}м, Зал: {event.hall_name}")
            print(f"       Формат: {event.format.value if event.format else 'Не указан'}")
            print(f"       Рекомендуется: {'Да' if event.recommend else 'Нет'}")
        
        # Тестируем конкретную пару концертов с коротким мероприятием
        print(f"\n🎯 ТЕСТИРУЕМ КОНКРЕТНУЮ ПАРУ КОНЦЕРТОВ:")
        
        # Находим пару концертов с промежутком
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        
        for i in range(len(concerts) - 1):
            current_concert = concerts[i]
            next_concert = concerts[i + 1]
            
            # Проверяем, что концерты в один день
            if current_concert.datetime.date() == next_concert.datetime.date():
                time_between = (next_concert.datetime - current_concert.datetime).total_seconds() / 60
                
                if time_between > 30:  # Промежуток больше 30 минут
                    print(f"\nКонцерт 1: {current_concert.datetime.strftime('%H:%M')} - {current_concert.name}")
                    print(f"Концерт 2: {next_concert.datetime.strftime('%H:%M')} - {next_concert.name}")
                    print(f"Промежуток: {time_between:.0f} минут")
                    
                    # Получаем залы
                    current_hall = session.exec(select(Hall).where(Hall.id == current_concert.hall_id)).first()
                    next_hall = session.exec(select(Hall).where(Hall.id == next_concert.hall_id)).first()
                    
                    # Вычисляем время окончания первого концерта
                    current_end = current_concert.datetime + timedelta(seconds=current_concert.duration.total_seconds())
                    print(f"Время окончания концерта 1: {current_end.strftime('%H:%M')}")
                    
                    # Ищем короткие мероприятия в промежутке
                    short_events_in_gap = []
                    for event, duration in short_events:
                        if (event.event_date >= current_end and 
                            event.event_date < next_concert.datetime):
                            short_events_in_gap.append((event, duration))
                    
                    print(f"Найдено коротких мероприятий в промежутке: {len(short_events_in_gap)}")
                    
                    if short_events_in_gap:
                        for event, duration in short_events_in_gap:
                            print(f"  📋 {event.event_name} ({event.event_date.strftime('%H:%M')})")
                            print(f"     Длительность: {duration}м, Зал: {event.hall_name}")
                            
                            # Проверяем, помещается ли мероприятие
                            event_end = event.event_date + timedelta(minutes=duration)
                            if event_end <= next_concert.datetime:
                                print(f"     ✅ Помещается во временной промежуток")
                                
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
                                
                                print(f"     Время переходов: {total_walk_time}м")
                                print(f"     Доступное время: {available_time:.0f}м")
                                print(f"     Требуемое время: {total_walk_time + duration}м")
                                
                                if total_walk_time + duration <= available_time:
                                    print(f"     ✅ Мероприятие доступно!")
                                else:
                                    print(f"     ❌ Недостаточно времени")
                            else:
                                print(f"     ❌ Не помещается во временной промежуток")
                        
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
                        
                        for event in available_events:
                            print(f"  ✅ {event['event_name']} ({event['event_date_display']})")
                            print(f"     Длительность: {event['duration']}, Зал: {event['hall_name']}")
                            print(f"     Время переходов: ~{event['total_walk_time']}м, Доступно: {event['available_time']}м")
                    
                    break  # Тестируем только первую подходящую пару
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск теста коротких мероприятий...")
    success = test_short_events()
    if success:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n💥 Тест завершен с ошибками!")
        sys.exit(1) 