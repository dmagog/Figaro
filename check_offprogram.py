#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from models import OffProgram
from sqlmodel import select

def check_offprogram_data():
    """Проверяет данные Офф-программы в базе данных"""
    try:
        session = next(get_session())
        events = session.exec(select(OffProgram)).all()
        
        print(f"Всего мероприятий: {len(events)}")
        
        if events:
            print("\nПервые 5 мероприятий:")
            for i, event in enumerate(events[:5]):
                print(f"{i+1}. ID: {event.id}")
                print(f"   Название: {event.event_name}")
                print(f"   Рекомендуется: {event.recommend} (тип: {type(event.recommend)})")
                print(f"   Формат: {event.format.value if event.format else 'Не указан'}")
                print()
            
            # Статистика по рекомендациям
            recommended_count = sum(1 for e in events if e.recommend)
            print(f"Рекомендуемых мероприятий: {recommended_count} из {len(events)}")
        else:
            print("❌ Данные Офф-программы не найдены в базе")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_offprogram_data() 