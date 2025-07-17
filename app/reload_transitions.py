#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from services.crud.data_loader import load_hall_transitions
from config_data_path import HALLS_TRANSITIONS_PATH
import pandas as pd

def reload_hall_transitions():
    """Перезагружает данные о переходах между залами"""
    
    print("🔄 Перезагружаем данные о переходах между залами...")
    
    try:
        # Читаем файл с переходами
        print("📖 Читаем файл переходов...")
        file_path = os.path.join(os.path.dirname(__file__), HALLS_TRANSITIONS_PATH)
        df_transitions = pd.read_excel(file_path)
        print(f"✅ Загружена матрица {df_transitions.shape}")
        
        # Подключаемся к базе данных
        print("🔌 Подключаемся к базе данных...")
        session = next(get_session())
        
        # Загружаем переходы
        print("💾 Загружаем переходы в базу...")
        load_hall_transitions(session, df_transitions)
        
        print("✅ Переходы успешно перезагружены!")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при перезагрузке переходов: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    reload_hall_transitions() 