#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from models import Hall, HallTransition
from sqlmodel import select

def test_transitions():
    """Тестирует наличие данных о переходах между залами"""
    
    print("🔍 Проверяем данные о переходах между залами")
    
    try:
        session = next(get_session())
        
        # Проверяем количество залов
        halls = session.exec(select(Hall)).all()
        print(f"✅ В базе данных: {len(halls)} залов")
        
        # Проверяем количество переходов
        transitions = session.exec(select(HallTransition)).all()
        print(f"✅ В базе данных: {len(transitions)} записей о переходах")
        
        if transitions:
            print("\n📊 Примеры переходов:")
            for i, transition in enumerate(transitions[:10]):
                from_hall = session.exec(select(Hall).where(Hall.id == transition.from_hall_id)).first()
                to_hall = session.exec(select(Hall).where(Hall.id == transition.to_hall_id)).first()
                print(f"  {i+1}. {from_hall.name if from_hall else 'Unknown'} → {to_hall.name if to_hall else 'Unknown'}: {transition.transition_time} мин")
            
            # Статистика
            print(f"\n📈 Статистика:")
            print(f"   Среднее время перехода: {sum(t.transition_time for t in transitions) / len(transitions):.1f} мин")
            print(f"   Минимальное время: {min(t.transition_time for t in transitions)} мин")
            print(f"   Максимальное время: {max(t.transition_time for t in transitions)} мин")
            
            # Проверяем конкретные переходы
            print(f"\n🔍 Проверяем конкретные переходы:")
            
            # Ищем залы "Дом музыки" и "ТЮЗ - Большой"
            dom_muzyki = session.exec(select(Hall).where(Hall.name.like('%Дом музыки%'))).first()
            tyuz = session.exec(select(Hall).where(Hall.name.like('%ТЮЗ%'))).first()
            
            if dom_muzyki and tyuz:
                print(f"   Зал 'Дом музыки': ID={dom_muzyki.id}")
                print(f"   Зал 'ТЮЗ': ID={tyuz.id}")
                
                # Проверяем переход Дом музыки → ТЮЗ
                transition1 = session.exec(
                    select(HallTransition)
                    .where(HallTransition.from_hall_id == dom_muzyki.id)
                    .where(HallTransition.to_hall_id == tyuz.id)
                ).first()
                
                if transition1:
                    print(f"   ✅ Дом музыки → ТЮЗ: {transition1.transition_time} мин")
                else:
                    print(f"   ❌ Переход Дом музыки → ТЮЗ не найден")
                
                # Проверяем переход ТЮЗ → Дом музыки
                transition2 = session.exec(
                    select(HallTransition)
                    .where(HallTransition.from_hall_id == tyuz.id)
                    .where(HallTransition.to_hall_id == dom_muzyki.id)
                ).first()
                
                if transition2:
                    print(f"   ✅ ТЮЗ → Дом музыки: {transition2.transition_time} мин")
                else:
                    print(f"   ❌ Переход ТЮЗ → Дом музыки не найден")
            else:
                print(f"   ⚠️ Не удалось найти залы 'Дом музыки' или 'ТЮЗ'")
                
        else:
            print("❌ Данные о переходах не найдены в базе")
            print("💡 Нужно загрузить данные через инициализацию базы")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_transitions() 