#!/usr/bin/env python3
"""
Тестовый скрипт для анализа производительности сопоставления покупателей с маршрутами
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_session
from services.crud.data_loader import update_customer_route_matches
from models import CustomerRouteMatch, Route, Purchase
from sqlmodel import select
from sqlalchemy import func
import time
import json

def analyze_customer_matching_performance():
    """Анализирует производительность сопоставления покупателей с маршрутами"""
    print("🔍 Анализ производительности сопоставления покупателей с маршрутами...")
    print("=" * 70)
    
    # Получаем сессию базы данных
    session = next(get_session())
    
    try:
        # Получаем базовую статистику
        total_routes = len(session.exec(select(Route)).all())
        total_customers = len(session.exec(select(Purchase.user_external_id).distinct()).all())
        
        print(f"📊 Базовая статистика:")
        print(f"   • Всего маршрутов: {total_routes:,}")
        print(f"   • Всего покупателей: {total_customers:,}")
        
        # Анализируем распределение концертов по покупателям
        customer_concerts_stats = session.exec(
            select(
                Purchase.user_external_id,
                func.count(func.distinct(Purchase.concert_id)).label('concert_count')
            )
            .group_by(Purchase.user_external_id)
        ).all()
        
        concert_counts = [stat[1] for stat in customer_concerts_stats]
        avg_concerts_per_customer = sum(concert_counts) / len(concert_counts) if concert_counts else 0
        max_concerts = max(concert_counts) if concert_counts else 0
        min_concerts = min(concert_counts) if concert_counts else 0
        
        print(f"\n🎵 Статистика концертов по покупателям:")
        print(f"   • Среднее количество концертов: {avg_concerts_per_customer:.1f}")
        print(f"   • Минимальное количество: {min_concerts}")
        print(f"   • Максимальное количество: {max_concerts}")
        
        # Анализируем распределение длины маршрутов
        route_lengths = []
        for route in session.exec(select(Route)).all():
            if route.Sostav:
                length = len([x.strip() for x in route.Sostav.split(',') if x.strip()])
                route_lengths.append(length)
        
        avg_route_length = sum(route_lengths) / len(route_lengths) if route_lengths else 0
        max_route_length = max(route_lengths) if route_lengths else 0
        min_route_length = min(route_lengths) if route_lengths else 0
        
        print(f"\n🛣️  Статистика длины маршрутов:")
        print(f"   • Средняя длина маршрута: {avg_route_length:.1f} концертов")
        print(f"   • Минимальная длина: {min_route_length}")
        print(f"   • Максимальная длина: {max_route_length}")
        
        # Тестируем производительность сопоставления
        print(f"\n⚡ Тестирование производительности сопоставления...")
        start_time = time.time()
        
        # Выполняем сопоставление
        update_customer_route_matches(session)
        
        total_time = time.time() - start_time
        
        # Получаем результаты сопоставления
        matches = session.exec(select(CustomerRouteMatch)).all()
        
        exact_matches = len([m for m in matches if m.match_type == 'exact'])
        partial_matches = len([m for m in matches if m.match_type == 'partial'])
        no_matches = len([m for m in matches if m.match_type == 'none'])
        
        print(f"\n📈 Результаты сопоставления:")
        print(f"   • Время выполнения: {total_time:.2f} секунд")
        print(f"   • Обработано покупателей: {len(matches):,}")
        print(f"   • Точных совпадений: {exact_matches:,} ({exact_matches/len(matches)*100:.1f}%)")
        print(f"   • Частичных совпадений: {partial_matches:,} ({partial_matches/len(matches)*100:.1f}%)")
        print(f"   • Без совпадений: {no_matches:,} ({no_matches/len(matches)*100:.1f}%)")
        
        # Анализируем производительность
        customers_per_second = len(matches) / total_time if total_time > 0 else 0
        routes_per_second = total_routes / total_time if total_time > 0 else 0
        
        print(f"\n🚀 Метрики производительности:")
        print(f"   • Покупателей в секунду: {customers_per_second:.1f}")
        print(f"   • Маршрутов в секунду: {routes_per_second:.1f}")
        print(f"   • Время на покупателя: {total_time/len(matches)*1000:.2f} мс")
        
        # Анализируем качество совпадений
        if partial_matches > 0:
            partial_match_percentages = [m.match_percentage for m in matches if m.match_percentage is not None]
            avg_partial_match = sum(partial_match_percentages) / len(partial_match_percentages) if partial_match_percentages else 0
            print(f"   • Средний процент частичных совпадений: {avg_partial_match:.1f}%")
        
        # Рекомендации
        print(f"\n💡 Рекомендации:")
        
        if total_time > 60:
            print(f"   ⚠️  Время выполнения велико ({total_time:.1f} сек), рассмотрите:")
            print(f"      - Увеличение размера батча")
            print(f"      - Параллельную обработку")
            print(f"      - Кэширование результатов")
        else:
            print(f"   ✅ Время выполнения приемлемо")
        
        if exact_matches / len(matches) < 0.1:
            print(f"   ⚠️  Мало точных совпадений ({exact_matches/len(matches)*100:.1f}%), возможно:")
            print(f"      - Проблемы с качеством данных")
            print(f"      - Недостаточно маршрутов")
        else:
            print(f"   ✅ Хороший процент точных совпадений")
        
        if customers_per_second < 10:
            print(f"   ⚠️  Низкая производительность ({customers_per_second:.1f} покупателей/сек)")
        else:
            print(f"   ✅ Хорошая производительность")
        
        # Сохраняем детальный отчет
        report = {
            'total_routes': total_routes,
            'total_customers': total_customers,
            'avg_concerts_per_customer': round(avg_concerts_per_customer, 2),
            'avg_route_length': round(avg_route_length, 2),
            'execution_time_seconds': round(total_time, 2),
            'customers_processed': len(matches),
            'exact_matches': exact_matches,
            'partial_matches': partial_matches,
            'no_matches': no_matches,
            'exact_match_percentage': round(exact_matches/len(matches)*100, 2),
            'partial_match_percentage': round(partial_matches/len(matches)*100, 2),
            'no_match_percentage': round(no_matches/len(matches)*100, 2),
            'customers_per_second': round(customers_per_second, 2),
            'routes_per_second': round(routes_per_second, 2),
            'time_per_customer_ms': round(total_time/len(matches)*1000, 2)
        }
        
        with open('customer_matching_performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 Детальный отчет сохранен в customer_matching_performance_report.json")
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    analyze_customer_matching_performance() 