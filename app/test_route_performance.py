#!/usr/bin/env python3
"""
Тестовый скрипт для проверки производительности системы маршрутов
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from services.crud.route_service import analyze_route_performance
import json

def main():
    """Основная функция тестирования производительности"""
    print("🔍 Анализ производительности системы маршрутов...")
    print("=" * 60)
    
    # Получаем сессию базы данных
    session = next(get_session())
    
    try:
        # Анализируем производительность
        metrics = analyze_route_performance(session)
        
        if 'error' in metrics:
            print(f"❌ Ошибка при анализе: {metrics['error']}")
            return
        
        # Выводим результаты
        print(f"📊 Общая статистика:")
        print(f"   • Всего маршрутов: {metrics['total_routes']:,}")
        print(f"   • Всего концертов: {metrics['total_concerts']:,}")
        print(f"   • Доступных маршрутов: {metrics['available_routes']:,}")
        print(f"   • Доступных концертов: {metrics['available_concerts']:,}")
        print(f"   • Процент доступности концертов: {metrics['availability_percentage']}%")
        
        print(f"\n📏 Характеристики маршрутов:")
        print(f"   • Средняя длина маршрута: {metrics['avg_route_length']} концертов")
        print(f"   • Минимальная длина: {metrics['min_route_length']} концертов")
        print(f"   • Максимальная длина: {metrics['max_route_length']} концертов")
        
        print(f"\n⚡ Производительность (тест на 10 маршрутах):")
        print(f"   • Без кэша: {metrics['time_without_cache_ms']} мс")
        print(f"   • С кэшем: {metrics['time_with_cache_ms']} мс")
        print(f"   • Улучшение: {metrics['performance_improvement_percent']}%")
        
        print(f"\n⏱️  Оценка времени полной проверки:")
        print(f"   • Ожидаемое время: {metrics['estimated_full_check_time_minutes']} минут")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        if metrics['performance_improvement_percent'] > 50:
            print(f"   ✅ Оптимизация работает эффективно!")
        else:
            print(f"   ⚠️  Возможно, нужны дополнительные оптимизации")
        
        if metrics['estimated_full_check_time_minutes'] > 30:
            print(f"   ⚠️  Полная проверка займет много времени, рассмотрите инкрементальные обновления")
        else:
            print(f"   ✅ Время полной проверки приемлемо")
        
        # Сохраняем результаты в JSON
        with open('route_performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Отчет сохранен в route_performance_report.json")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    main() 