#!/usr/bin/env python3
"""
Отладочный скрипт для проверки маппинга между файлами
"""
import pandas as pd

def debug_mapping():
    print("=== ПРОВЕРКА МАППИНГА МЕЖДУ ФАЙЛАМИ ===\n")
    
    try:
        artists_df = pd.read_excel('/app/data/ArtistDetails-good.xlsx')
        concerts_df = pd.read_excel('/app/data/ConcertList-good.xlsx')
        
        print("1. КОЛОНКИ В ФАЙЛАХ:")
        print(f"Концерты: {concerts_df.columns.tolist()}")
        print(f"Артисты: {artists_df.columns.tolist()}")
        
        print("\n2. ПЕРВЫЕ 10 ЗАПИСЕЙ КОНЦЕРТОВ:")
        print(concerts_df.head(10)[['ShowNum', 'ShowId', 'ShowName']])
        
        print("\n3. ПЕРВЫЕ 10 ЗАПИСЕЙ АРТИСТОВ:")
        print(artists_df.head(10)[['ShowNum', 'Artists']])
        
        print("\n4. ПРОВЕРКА СООТВЕТСТВИЯ ShowNum И ShowId:")
        for i in range(1, 11):
            concert_row = concerts_df[concerts_df['ShowNum'] == i]
            artist_rows = artists_df[artists_df['ShowNum'] == i]
            
            if not concert_row.empty:
                show_id = concert_row.iloc[0]['ShowId']
                show_name = concert_row.iloc[0]['ShowName']
                artists = artist_rows['Artists'].tolist() if not artist_rows.empty else []
                
                print(f"ShowNum={i}: ShowId={show_id}, Name='{show_name}', Artists={artists}")
        
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    debug_mapping() 