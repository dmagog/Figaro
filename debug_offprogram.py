#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from models import OffProgram
from sqlmodel import select

def debug_offprogram():
    """Диагностика данных Офф-программы"""
    try:
        session = next(get_session())
        events = session.exec(select(OffProgram)).all()
        
        print(f"Всего мероприятий: {len(events)}")
        
        if events:
            print("\n=== ДИАГНОСТИКА ПОЛЯ RECOMMEND ===")
            for i, event in enumerate(events[:5]):
                print(f"\n{i+1}. Мероприятие: {event.event_name}")
                print(f"   recommend = {event.recommend}")
                print(f"   тип: {type(event.recommend)}")
                print(f"   str(): {str(event.recommend)}")
                print(f"   repr(): {repr(event.recommend)}")
                
                # Проверяем наше условие
                is_recommended = str(event.recommend).lower() in ('1', 'true', 'yes', 'да')
                print(f"   Наше условие: {is_recommended}")
            
            # Статистика
            print(f"\n=== СТАТИСТИКА ===")
            unique_values = set(str(e.recommend) for e in events)
            print(f"Уникальные значения recommend: {unique_values}")
            
            recommended_count = sum(1 for e in events if str(e.recommend).lower() in ('1', 'true', 'yes', 'да'))
            print(f"Рекомендуемых (по нашему условию): {recommended_count}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_offprogram() 