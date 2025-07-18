#!/usr/bin/env python3
"""
Поиск реальных возможностей посещения офф-программы с учетом времени
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def find_real_opportunities():
    """Ищет реальные возможности посещения офф-программы"""
    
    try:
        session = next(get_session())
        
        print("🔍 ПОИСК РЕАЛЬНЫХ ВОЗМОЖНОСТЕЙ ПОСЕЩЕНИЯ ОФФ-ПРОГРАММЫ")
        print("=" * 70)
        
        # Получаем все мероприятия офф-программы с короткой продолжительностью
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
        
        print(f"📊 Найдено {len(short_events)} мероприятий с продолжительностью до 1 часа")
        
        # Получаем концерты, отсортированные по времени
        concerts = session.exec(select(Concert).order_by(Concert.datetime)).all()
        
        # Ищем пары концертов с промежутками
        opportunities = []
        
        for i in range(len(concerts) - 1):
            current_concert = concerts[i]
            next_concert = concerts[i + 1]
            
            # Проверяем, что концерты в один день
            if current_concert.datetime.date() == next_concert.datetime.date():
                time_between = (next_concert.datetime - current_concert.datetime).total_seconds() / 60
                
                if time_between > 30:  # Промежуток больше 30 минут
                    # Вычисляем время окончания первого концерта
                    current_end = current_concert.datetime + timedelta(seconds=current_concert.duration.total_seconds())
                    
                    # Ищем короткие мероприятия в промежутке
                    for event, duration in short_events:
                        if (event.event_date >= current_end and 
                            event.event_date < next_concert.datetime):
                            
                            # Проверяем, помещается ли мероприятие
                            event_end = event.event_date + timedelta(minutes=duration)
                            if event_end <= next_concert.datetime:
                                # Рассчитываем время переходов
                                walk_time_to_event = 10  # К Инфоцентру
                                walk_time_from_event = 10  # От Инфоцентра
                                total_walk_time = walk_time_to_event + walk_time_from_event
                                available_time = (next_concert.datetime - current_end).total_seconds() / 60
                                
                                if total_walk_time + duration <= available_time:
                                    opportunities.append({
                                        'current_concert': current_concert,
                                        'next_concert': next_concert,
                                        'event': event,
                                        'duration': duration,
                                        'time_between': time_between,
                                        'available_time': available_time,
                                        'total_walk_time': total_walk_time
                                    })
        
        print(f"🎯 Найдено {len(opportunities)} реальных возможностей:")
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\n{i}. {opp['current_concert'].datetime.strftime('%H:%M')} - {opp['current_concert'].name}")
            print(f"   {opp['next_concert'].datetime.strftime('%H:%M')} - {opp['next_concert'].name}")
            print(f"   Промежуток: {opp['time_between']:.0f} минут")
            print(f"   Мероприятие: {opp['event'].event_name} ({opp['event'].event_date.strftime('%H:%M')})")
            print(f"   Длительность мероприятия: {opp['duration']} минут")
            print(f"   Время переходов: {opp['total_walk_time']} минут")
            print(f"   Доступное время: {opp['available_time']:.0f} минут")
            print(f"   Требуемое время: {opp['total_walk_time'] + opp['duration']} минут")
            print(f"   Остаток времени: {opp['available_time'] - (opp['total_walk_time'] + opp['duration']):.0f} минут")
        
        # Тестируем нашу функцию на первой возможности
        if opportunities:
            print(f"\n🧪 ТЕСТИРУЕМ НАШУ ФУНКЦИЮ:")
            
            opp = opportunities[0]
            current_concert = opp['current_concert']
            next_concert = opp['next_concert']
            
            # Получаем залы
            current_hall = session.exec(select(Hall).where(Hall.id == current_concert.hall_id)).first()
            next_hall = session.exec(select(Hall).where(Hall.id == next_concert.hall_id)).first()
            
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
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск поиска реальных возможностей...")
    success = find_real_opportunities()
    if success:
        print("\n✅ Поиск завершен успешно!")
    else:
        print("\n💥 Поиск завершен с ошибками!")
        sys.exit(1) 