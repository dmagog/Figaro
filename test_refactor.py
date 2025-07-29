#!/usr/bin/env python3
"""
Тестовый файл для проверки перенесенных функций
"""
import sys
import os
sys.path.append('/app')

def test_imports():
    print("=== ТЕСТИРОВАНИЕ ИМПОРТОВ ===")
    
    try:
        # Тестируем импорт из нового места
        from app.services.user.utils import get_all_festival_days_with_visit_status, group_concerts_by_day
        print("✅ Импорт функций из app.services.user.utils успешен")
        
        # Проверяем, что функции доступны
        print(f"✅ get_all_festival_days_with_visit_status: {get_all_festival_days_with_visit_status}")
        print(f"✅ group_concerts_by_day: {group_concerts_by_day}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n🎉 Все тесты прошли успешно!")
    else:
        print("\n�� Тесты не прошли!") 