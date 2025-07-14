#!/usr/bin/env python3
"""
Скрипт для тестирования производительности загрузки данных
"""
import time
import pandas as pd
from database.database import get_session, init_db
from services.crud import data_loader
from config_data_path import HALLS_LIST_PATH, CONCERTS_PATH, ARTISTS_PATH, PROGRAMM_PATH, TRANSACTIONS_PATH


def test_loading_performance():
    """Тестирует производительность загрузки данных"""
    print("🚀 Тестирование производительности загрузки данных")
    print("=" * 60)
    
    # Загружаем данные в память
    print("📁 Загружаем Excel файлы в память...")
    start_time = time.time()
    
    halls_df = pd.read_excel(HALLS_LIST_PATH)
    concerts_df = pd.read_excel(CONCERTS_PATH)
    artists_df = pd.read_excel(ARTISTS_PATH)
    compositions_df = pd.read_excel(PROGRAMM_PATH)
    purchases_df = pd.read_excel(TRANSACTIONS_PATH)
    
    load_time = time.time() - start_time
    print(f"✅ Файлы загружены за {load_time:.2f} секунд")
    
    print(f"\n📊 Статистика файлов:")
    print(f"  - Залы: {len(halls_df):,} записей")
    print(f"  - Концерты: {len(concerts_df):,} записей")
    print(f"  - Артисты: {len(artists_df):,} записей")
    print(f"  - Композиции: {len(compositions_df):,} записей")
    print(f"  - Покупки: {len(purchases_df):,} записей")
    print(f"  - Всего записей: {len(halls_df) + len(concerts_df) + len(artists_df) + len(compositions_df) + len(purchases_df):,}")
    
    # Тестируем загрузку в базу данных
    print(f"\n🗄️  Тестируем загрузку в базу данных...")
    print(f"Размер батча: {data_loader.BATCH_SIZE}")
    
    start_time = time.time()
    
    # Инициализируем базу
    init_db(demostart=True)
    
    total_time = time.time() - start_time
    
    print(f"\n✅ Загрузка завершена!")
    print(f"⏱️  Общее время: {total_time:.2f} секунд")
    print(f"📈 Скорость: {(len(halls_df) + len(concerts_df) + len(artists_df) + len(compositions_df) + len(purchases_df)) / total_time:.0f} записей/сек")
    
    # Проверяем результаты
    with next(get_session()) as session:
        from models import Hall, Concert, Artist, Composition, Purchase
        
        from sqlmodel import select
        halls_count = len(session.exec(select(Hall)).all())
        concerts_count = len(session.exec(select(Concert)).all())
        artists_count = len(session.exec(select(Artist)).all())
        compositions_count = len(session.exec(select(Composition)).all())
        purchases_count = len(session.exec(select(Purchase)).all())
        
        print(f"\n📋 Результаты в базе:")
        print(f"  - Залы: {halls_count}")
        print(f"  - Концерты: {concerts_count}")
        print(f"  - Артисты: {artists_count}")
        print(f"  - Композиции: {compositions_count}")
        print(f"  - Покупки: {purchases_count}")


if __name__ == "__main__":
    test_loading_performance() 