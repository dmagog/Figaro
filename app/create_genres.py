#!/usr/bin/env python3
"""
Скрипт для создания жанров и связывания их с концертами
"""

from database.database import get_session
from models import Concert, Genre, ConcertGenreLink
from sqlmodel import select
from collections import defaultdict

def create_genres_and_links():
    """Создает жанры и связывает их с концертами"""
    session = next(get_session())
    
    try:
        # Получаем все уникальные жанры из концертов
        concerts = session.exec(select(Concert)).all()
        
        # Собираем уникальные жанры
        unique_genres = set()
        for concert in concerts:
            if concert.genre:
                # Обрабатываем жанр как единое целое (не разбиваем по запятым)
                unique_genres.add(concert.genre.strip())
        
        print(f"Найдено {len(unique_genres)} уникальных жанров:")
        for genre_name in sorted(unique_genres):
            print(f"  - {genre_name}")
        
        # Создаем жанры в базе данных
        genre_map = {}
        for genre_name in unique_genres:
            # Проверяем, существует ли уже такой жанр
            existing_genre = session.exec(
                select(Genre).where(Genre.name == genre_name)
            ).first()
            
            if existing_genre:
                genre_map[genre_name] = existing_genre
                print(f"Жанр '{genre_name}' уже существует (ID: {existing_genre.id})")
            else:
                # Создаем новый жанр
                new_genre = Genre(name=genre_name)
                session.add(new_genre)
                session.commit()
                session.refresh(new_genre)
                genre_map[genre_name] = new_genre
                print(f"Создан жанр '{genre_name}' (ID: {new_genre.id})")
        
        # Связываем концерты с жанрами
        links_created = 0
        for concert in concerts:
            if concert.genre:
                # Обрабатываем жанр как единое целое
                genre_name = concert.genre.strip()
                
                if genre_name in genre_map:
                    genre = genre_map[genre_name]
                    
                    # Проверяем, существует ли уже связь
                    existing_link = session.exec(
                        select(ConcertGenreLink).where(
                            ConcertGenreLink.concert_id == concert.id,
                            ConcertGenreLink.genre_id == genre.id
                        )
                    ).first()
                    
                    if not existing_link:
                        # Создаем связь
                        link = ConcertGenreLink(
                            concert_id=concert.id,
                            genre_id=genre.id
                        )
                        session.add(link)
                        links_created += 1
        
        session.commit()
        print(f"\nСоздано {links_created} связей концерт-жанр")
        
        # Статистика
        total_genres = len(genre_map)
        total_concerts = len(concerts)
        concerts_with_genres = sum(1 for c in concerts if c.genre)
        
        print(f"\n📊 Статистика:")
        print(f"  • Всего жанров: {total_genres}")
        print(f"  • Всего концертов: {total_concerts}")
        print(f"  • Концертов с жанрами: {concerts_with_genres}")
        print(f"  • Связей создано: {links_created}")
        
        return True
        
    except Exception as e:
        print(f"Ошибка: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🎵 Создание жанров и связывание с концертами...")
    success = create_genres_and_links()
    if success:
        print("✅ Готово!")
    else:
        print("❌ Ошибка при создании жанров") 