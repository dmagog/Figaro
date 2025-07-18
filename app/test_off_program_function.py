#!/usr/bin/env python3
"""
Тест функции офф-программы с искусственными данными
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import find_available_off_program_events
from models import OffProgram, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_off_program_function():
    """Тестирует функцию офф-программы с искусственными данными"""
    
    try:
        session = next(get_session())
        
        print("🧪 ТЕСТ ФУНКЦИИ ОФФ-ПРОГРАММЫ С ИСКУССТВЕННЫМИ ДАННЫМИ")
        print("=" * 70)
        
        # Создаем искусственные данные для тестирования
        # Концерт 1: 13:00-13:45 (45 минут)
        # Концерт 2: 15:00-15:45 (45 минут)
        # Промежуток: 75 минут
        # Мероприятие офф-программы: 14:00-14:30 (30 минут)
        
        # Получаем существующие залы
        halls = session.exec(select(Hall)).all()
        if len(halls) < 2:
            print("❌ Недостаточно залов для тестирования")
            return False
        
        hall1 = halls[0]
        hall2 = halls[1]
        
        print(f"Используем залы: {hall1.name} и {hall2.name}")
        
        # Создаем тестовые данные концертов
        current_concert_data = {
            'concert': {
                'id': 9991,
                'name': 'Тестовый концерт 1',
                'datetime': datetime(2022, 7, 1, 13, 0),  # 13:00
                'duration': timedelta(minutes=45),
                'hall': {
                    'id': hall1.id,
                    'name': hall1.name
                }
            }
        }
        
        next_concert_data = {
            'concert': {
                'id': 9992,
                'name': 'Тестовый концерт 2',
                'datetime': datetime(2022, 7, 1, 15, 0),  # 15:00
                'duration': timedelta(minutes=45),
                'hall': {
                    'id': hall2.id,
                    'name': hall2.name
                }
            }
        }
        
        print(f"Тестовые концерты:")
        print(f"Концерт 1: {current_concert_data['concert']['datetime'].strftime('%H:%M')} - {current_concert_data['concert']['name']}")
        print(f"Концерт 2: {next_concert_data['concert']['datetime'].strftime('%H:%M')} - {next_concert_data['concert']['name']}")
        
        # Вычисляем промежуток
        time_between = (next_concert_data['concert']['datetime'] - current_concert_data['concert']['datetime']).total_seconds() / 60
        print(f"Промежуток: {time_between:.0f} минут")
        
        # Вычисляем время окончания первого концерта
        current_end = current_concert_data['concert']['datetime'] + current_concert_data['concert']['duration']
        print(f"Время окончания концерта 1: {current_end.strftime('%H:%M')}")
        
        # Создаем тестовое мероприятие офф-программы
        test_event = OffProgram(
            id=9999,
            event_num=9999,
            event_name="Тестовый воркшоп",
            event_date=datetime(2022, 7, 1, 14, 0),  # 14:00
            event_long="00:30",  # 30 минут
            hall_name="Инфоцентр",
            format="Воркшоп",
            recommend=True
        )
        
        print(f"Тестовое мероприятие: {test_event.event_name} ({test_event.event_date.strftime('%H:%M')})")
        print(f"Длительность: {test_event.event_long}, Зал: {test_event.hall_name}")
        
        # Проверяем, помещается ли мероприятие
        event_duration = timedelta(minutes=30)
        event_end = test_event.event_date + event_duration
        print(f"Время окончания мероприятия: {event_end.strftime('%H:%M')}")
        
        if event_end <= next_concert_data['concert']['datetime']:
            print("✅ Мероприятие помещается во временной промежуток")
            
            # Рассчитываем время переходов
            walk_time_to_event = 10  # К Инфоцентру
            walk_time_from_event = 10  # От Инфоцентра
            total_walk_time = walk_time_to_event + walk_time_from_event
            available_time = (next_concert_data['concert']['datetime'] - current_end).total_seconds() / 60
            
            print(f"Время перехода к мероприятию: {walk_time_to_event}м")
            print(f"Время перехода от мероприятия: {walk_time_from_event}м")
            print(f"Общее время переходов: {total_walk_time}м")
            print(f"Доступное время: {available_time:.0f}м")
            print(f"Длительность мероприятия: {event_duration.total_seconds() / 60:.0f}м")
            print(f"Требуемое время: {total_walk_time + event_duration.total_seconds() / 60:.0f}м")
            
            if total_walk_time + event_duration.total_seconds() / 60 <= available_time:
                print("✅ Мероприятие доступно!")
            else:
                print("❌ Недостаточно времени")
        else:
            print("❌ Мероприятие не помещается во временной промежуток")
        
        # Тестируем нашу функцию
        print(f"\n🧪 ТЕСТИРУЕМ НАШУ ФУНКЦИЮ:")
        
        # Временно добавляем тестовое мероприятие в базу
        session.add(test_event)
        session.commit()
        
        try:
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
        
        finally:
            # Удаляем тестовое мероприятие
            session.delete(test_event)
            session.commit()
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск теста функции офф-программы...")
    success = test_off_program_function()
    if success:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n💥 Тест завершен с ошибками!")
        sys.exit(1) 