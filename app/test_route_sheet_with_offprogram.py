#!/usr/bin/env python3
"""
Тест маршрутного листа с офф-программой
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from routes.user import get_user_route_sheet
from models import Purchase, Concert, Hall
from datetime import datetime, timedelta
from sqlmodel import select

def test_route_sheet_with_offprogram():
    """Тестирует маршрутный лист с офф-программой"""
    
    try:
        session = next(get_session())
        
        print("🎯 ТЕСТ МАРШРУТНОГО ЛИСТА С ОФФ-ПРОГРАММОЙ")
        print("=" * 60)
        
        # Получаем тестового пользователя (первого с покупками)
        purchases = session.exec(select(Purchase).limit(1)).all()
        
        if not purchases:
            print("❌ Нет покупок для тестирования")
            return False
        
        test_purchase = purchases[0]
        user_external_id = test_purchase.external_id
        
        print(f"Тестируем пользователя: {user_external_id}")
        
        # Получаем маршрутный лист
        route_sheet = get_user_route_sheet(session, user_external_id, [])
        
        print(f"📊 Статистика маршрутного листа:")
        print(f"   Концертов: {route_sheet['summary']['total_concerts']}")
        print(f"   Дней: {route_sheet['summary']['total_days']}")
        print(f"   Залов: {route_sheet['summary']['total_halls']}")
        print(f"   Жанров: {route_sheet['summary']['total_genres']}")
        
        # Проверяем концерты по дням
        concerts_by_day = route_sheet['concerts_by_day']
        print(f"\n📅 Концерты по дням:")
        
        total_off_program_events = 0
        
        for day_index, day_concerts in concerts_by_day.items():
            print(f"\nДень {day_index}:")
            
            for i, concert in enumerate(day_concerts):
                concert_name = concert['concert']['name']
                concert_time = concert['concert']['datetime'].strftime('%H:%M')
                hall_name = concert['concert']['hall']['name'] if concert['concert']['hall'] else 'Неизвестный зал'
                
                print(f"  {i+1}. {concert_time} - {concert_name} ({hall_name})")
                
                # Проверяем информацию о переходе
                transition_info = concert.get('transition_info')
                if transition_info:
                    status = transition_info.get('status', 'unknown')
                    walk_time = transition_info.get('walk_time', 0)
                    print(f"     Переход: {status} (~{walk_time}м)")
                
                # Проверяем мероприятия офф-программы
                off_program_events = concert.get('off_program_events', [])
                if off_program_events:
                    print(f"     🎭 Доступно мероприятий офф-программы: {len(off_program_events)}")
                    total_off_program_events += len(off_program_events)
                    
                    for j, event in enumerate(off_program_events, 1):
                        print(f"       {j}. {event['event_name']} ({event['event_date_display']})")
                        print(f"          Длительность: {event['duration']}, Зал: {event['hall_name']}")
                        print(f"          Время переходов: ~{event['total_walk_time']}м")
                        print(f"          Формат: {event['format']}")
                        print(f"          Рекомендуется: {'Да' if event['recommend'] else 'Нет'}")
        
        print(f"\n🎉 ИТОГО:")
        print(f"   Найдено мероприятий офф-программы: {total_off_program_events}")
        
        if total_off_program_events > 0:
            print("✅ Офф-программа успешно интегрирована в маршрутный лист!")
        else:
            print("ℹ️  Мероприятия офф-программы не найдены (это может быть нормально)")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 Запуск теста маршрутного листа...")
    success = test_route_sheet_with_offprogram()
    if success:
        print("\n✅ Тест завершен успешно!")
    else:
        print("\n💥 Тест завершен с ошибками!")
        sys.exit(1) 