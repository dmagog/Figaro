#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from models import Hall, HallTransition
from sqlmodel import select
import pandas as pd
from config_data_path import HALLS_TRANSITIONS_PATH

def test_hall_transitions():
    """Тестирует загрузку данных о переходах между залами"""
    
    print("🔍 Тестирование загрузки данных о переходах между залами")
    
    # Проверяем наличие файла
    if not os.path.exists(HALLS_TRANSITIONS_PATH):
        print(f"❌ Файл {HALLS_TRANSITIONS_PATH} не найден!")
        return False
    
    try:
        # Читаем Excel файл
        print("📖 Читаем файл переходов между залами...")
        df = pd.read_excel(HALLS_TRANSITIONS_PATH)
        print(f"✅ Загружена матрица {df.shape}")
        print(f"   Колонки: {df.columns.tolist()}")
        
        # Подключаемся к базе данных
        print("🔌 Подключаемся к базе данных...")
        session = next(get_session())
        
        # Проверяем количество залов
        halls = session.exec(select(Hall)).all()
        print(f"✅ В базе данных: {len(halls)} залов")
        
        # Проверяем количество переходов
        transitions = session.exec(select(HallTransition)).all()
        print(f"✅ В базе данных: {len(transitions)} записей о переходах")
        
        if transitions:
            print("\n📊 Примеры переходов:")
            for i, transition in enumerate(transitions[:5]):
                from_hall = session.exec(select(Hall).where(Hall.id == transition.from_hall_id)).first()
                to_hall = session.exec(select(Hall).where(Hall.id == transition.to_hall_id)).first()
                print(f"  {i+1}. {from_hall.name} → {to_hall.name}: {transition.transition_time} мин")
            
            # Статистика
            print(f"\n📈 Статистика:")
            print(f"   Среднее время перехода: {sum(t.transition_time for t in transitions) / len(transitions):.1f} мин")
            print(f"   Минимальное время: {min(t.transition_time for t in transitions)} мин")
            print(f"   Максимальное время: {max(t.transition_time for t in transitions)} мин")
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
    test_hall_transitions() 