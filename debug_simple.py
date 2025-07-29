#!/usr/bin/env python3
"""
Простой отладочный скрипт для анализа данных
"""
import pandas as pd

def debug_simple():
    print("=== ПРОСТОЙ АНАЛИЗ ДАННЫХ ===\n")
    
    # 1. Проверяем данные из Excel файла
    print("1. ДАННЫЕ ИЗ EXCEL ФАЙЛА:")
    try:
        artists_df = pd.read_excel('/app/data/ArtistDetails-good.xlsx')
        concerts_df = pd.read_excel('/app/data/ConcertList-good.xlsx')
        
        print(f"Концерты в Excel: {len(concerts_df)}")
        print(f"Артисты в Excel: {len(artists_df)}")
        
        # Показываем концерт с ShowNum=5
        concert_5_excel = concerts_df[concerts_df['ShowNum'] == 5]
        print(f"\nКонцерт с ShowNum=5 в Excel:")
        print(concert_5_excel)
        
        # Показываем артистов для концерта 5
        artists_5_excel = artists_df[artists_df['ShowNum'] == 5]
        print(f"\nАртисты для концерта 5 в Excel:")
        print(artists_5_excel[['ShowNum', 'Artists']])
        
        # Показываем первые 10 концертов
        print(f"\nПервые 10 концертов:")
        print(concerts_df.head(10)[['ShowNum', 'Name']])
        
        # Показываем первые 10 артистов
        print(f"\nПервые 10 артистов:")
        print(artists_df.head(10)[['ShowNum', 'Artists']])
        
    except Exception as e:
        print(f"Ошибка при чтении Excel файлов: {e}")

if __name__ == "__main__":
    debug_simple() 