#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отсутствия дублирования инициализации AvailableRoute
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from services.crud.route_service import ensure_available_routes_exist, get_available_routes_stats
import time

def test_route_initialization():
    """Тестирует инициализацию маршрутов на предмет дублирования"""
    print("🧪 Тестирование инициализации AvailableRoute...")
    print("=" * 60)
    
    # Получаем сессию базы данных
    session = next(get_session())
    
    try:
        # Получаем начальную статистику
        initial_stats = get_available_routes_stats(session)
        print(f"📊 Начальное состояние:")
        print(f"   • Всего маршрутов: {initial_stats['total_routes']:,}")
        print(f"   • Доступных маршрутов: {initial_stats['available_routes']:,}")
        print(f"   • Процент доступности: {initial_stats['availability_percentage']}%")
        
        # Тестируем первую инициализацию
        print(f"\n🔄 Первая попытка инициализации...")
        start_time = time.time()
        was_initialized_1 = ensure_available_routes_exist(session)
        time_1 = time.time() - start_time
        
        print(f"   • Результат: {'Инициализированы' if was_initialized_1 else 'Уже существовали'}")
        print(f"   • Время выполнения: {time_1:.2f} сек")
        
        # Получаем статистику после первой попытки
        stats_after_1 = get_available_routes_stats(session)
        print(f"   • Доступных маршрутов после: {stats_after_1['available_routes']:,}")
        
        # Тестируем вторую инициализацию (должна быть быстрой)
        print(f"\n🔄 Вторая попытка инициализации...")
        start_time = time.time()
        was_initialized_2 = ensure_available_routes_exist(session)
        time_2 = time.time() - start_time
        
        print(f"   • Результат: {'Инициализированы' if was_initialized_2 else 'Уже существовали'}")
        print(f"   • Время выполнения: {time_2:.2f} сек")
        
        # Получаем статистику после второй попытки
        stats_after_2 = get_available_routes_stats(session)
        print(f"   • Доступных маршрутов после: {stats_after_2['available_routes']:,}")
        
        # Анализируем результаты
        print(f"\n📈 Анализ результатов:")
        
        if was_initialized_1 and not was_initialized_2:
            print(f"   ✅ Первая инициализация прошла успешно")
            print(f"   ✅ Вторая инициализация пропущена (дублирования нет)")
        elif was_initialized_1 and was_initialized_2:
            print(f"   ❌ ОБНАРУЖЕНО ДУБЛИРОВАНИЕ: обе инициализации выполнились")
        elif not was_initialized_1 and not was_initialized_2:
            print(f"   ✅ Обе инициализации пропущены (маршруты уже существовали)")
        else:
            print(f"   ⚠️  Неожиданный результат: первая={was_initialized_1}, вторая={was_initialized_2}")
        
        # Проверяем консистентность данных
        if stats_after_1['available_routes'] == stats_after_2['available_routes']:
            print(f"   ✅ Данные консистентны между попытками")
        else:
            print(f"   ❌ НЕКОНСИСТЕНТНОСТЬ: количество изменилось между попытками")
        
        # Проверяем производительность
        if time_2 < time_1 * 0.1:  # Вторая попытка должна быть в 10 раз быстрее
            print(f"   ✅ Вторая попытка значительно быстрее (оптимизация работает)")
        else:
            print(f"   ⚠️  Вторая попытка не значительно быстрее")
        
        print(f"\n🎯 Итоговое состояние:")
        print(f"   • Всего маршрутов: {stats_after_2['total_routes']:,}")
        print(f"   • Доступных маршрутов: {stats_after_2['available_routes']:,}")
        print(f"   • Процент доступности: {stats_after_2['availability_percentage']}%")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if was_initialized_1 and not was_initialized_2:
            print(f"   ✅ Система работает корректно, дублирования нет")
        else:
            print(f"   ⚠️  Возможны проблемы с логикой инициализации")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_route_initialization() 