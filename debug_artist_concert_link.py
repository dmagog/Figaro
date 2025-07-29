#!/usr/bin/env python3
"""
Отладочный скрипт для анализа связей между концертами и артистами
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database.database import get_session
from app.models.concert import Concert
from app.models.artist import Artist
from app.models.concert_artist_link import ConcertArtistLink
from sqlmodel import select
import pandas as pd

def debug_artist_concert_link():
    session = next(get_session())
    try:
        print("=== АНАЛИЗ СВЯЗЕЙ КОНЦЕРТОВ И АРТИСТОВ ===\n")
        
        # 1. Проверяем данные из Excel файла
        print("1. ДАННЫЕ ИЗ EXCEL ФАЙЛА:")
        artists_df = pd.read_excel('app/data/ArtistDetails-good.xlsx')
        concerts_df = pd.read_excel('app/data/ConcertList-good.xlsx')
        
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
        
        # 2. Проверяем данные в базе
        print("\n2. ДАННЫЕ В БАЗЕ:")
        
        # Концерт с external_id=5
        concert_5_db = session.exec(select(Concert).where(Concert.external_id == 5)).first()
        if concert_5_db:
            print(f"Концерт с external_id=5 в базе:")
            print(f"  ID: {concert_5_db.id}")
            print(f"  external_id: {concert_5_db.external_id}")
            print(f"  Название: {concert_5_db.name}")
            print(f"  Дата: {concert_5_db.datetime}")
        else:
            print("❌ Концерт с external_id=5 не найден в базе!")
        
        # Артисты для концерта 5
        if concert_5_db:
            artist_links = session.exec(
                select(ConcertArtistLink)
                .where(ConcertArtistLink.concert_id == concert_5_db.id)
            ).all()
            
            print(f"\nСвязи артистов для концерта {concert_5_db.id}:")
            for link in artist_links:
                artist = session.exec(select(Artist).where(Artist.id == link.artist_id)).first()
                print(f"  Artist ID: {link.artist_id}, Name: {artist.name if artist else 'NOT FOUND'}")
        
        # 3. Проверяем всех артистов в базе
        print("\n3. ВСЕ АРТИСТЫ В БАЗЕ:")
        all_artists = session.exec(select(Artist)).all()
        print(f"Всего артистов: {len(all_artists)}")
        
        # Ищем артиста "Симфонический хор Свердловской филармонии"
        target_artist = session.exec(
            select(Artist).where(Artist.name == "Симфонический хор Свердловской филармонии")
        ).first()
        
        if target_artist:
            print(f"\nНайден артист: {target_artist.name} (ID: {target_artist.id})")
            
            # Проверяем, в каких концертах он участвует
            artist_concerts = session.exec(
                select(ConcertArtistLink)
                .where(ConcertArtistLink.artist_id == target_artist.id)
            ).all()
            
            print(f"Концерты артиста '{target_artist.name}':")
            for link in artist_concerts:
                concert = session.exec(select(Concert).where(Concert.id == link.concert_id)).first()
                print(f"  Concert ID: {link.concert_id}, external_id: {concert.external_id if concert else 'NOT FOUND'}, Name: {concert.name if concert else 'NOT FOUND'}")
        else:
            print("❌ Артист 'Симфонический хор Свердловской филармонии' не найден в базе!")
        
        # 4. Проверяем функцию load_artists
        print("\n4. АНАЛИЗ ФУНКЦИИ LOAD_ARTISTS:")
        print("Проверяем, как работает маппинг concert.external_id -> concert.id:")
        
        concerts_map = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
        print(f"Маппинг концертов: {concerts_map}")
        
        if 5 in concerts_map:
            print(f"Концерт с external_id=5 имеет ID: {concerts_map[5]}")
        else:
            print("❌ Концерт с external_id=5 не найден в маппинге!")
        
    finally:
        session.close()

if __name__ == "__main__":
    debug_artist_concert_link() 