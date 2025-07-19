#!/usr/bin/env python3
"""
Скрипт для проверки данных о жанрах и концертах
"""

from database.database import get_session
from models import Concert, Genre, ConcertGenreLink
from sqlmodel import select
from sqlalchemy import func

def check_genre_data():
    """Проверяет данные о жанрах и концертах"""
    session = next(get_session())
    
    try:
        # 1. Общее количество концертов
        total_concerts = session.exec(select(func.count(Concert.id))).first()
        print(f"📊 Общее количество концертов: {total_concerts}")
        
        # 2. Концерты с жанрами
        concerts_with_genres = session.exec(
            select(func.count(Concert.id))
            .where(Concert.genre.is_not(None))
        ).first()
        print(f"📊 Концертов с жанрами: {concerts_with_genres}")
        
        # 3. Общее количество связей жанр-концерт
        total_links = session.exec(select(func.count(ConcertGenreLink.concert_id))).first()
        print(f"📊 Общее количество связей жанр-концерт: {total_links}")
        
        # 4. Проверяем дублирующиеся связи
        duplicate_links = session.exec(
            select(ConcertGenreLink.concert_id, func.count(ConcertGenreLink.concert_id))
            .group_by(ConcertGenreLink.concert_id)
            .having(func.count(ConcertGenreLink.concert_id) > 1)
        ).all()
        
        if duplicate_links:
            print(f"⚠️  Найдено {len(duplicate_links)} концертов с несколькими жанрами:")
            for concert_id, count in duplicate_links:
                print(f"   Концерт {concert_id}: {count} жанров")
        else:
            print("✅ Все концерты имеют ровно один жанр")
        
        # 5. Проверяем концерты без жанров
        concerts_without_genres = session.exec(
            select(Concert.id, Concert.name, Concert.genre)
            .where(Concert.genre.is_(None))
        ).all()
        
        if concerts_without_genres:
            print(f"⚠️  Найдено {len(concerts_without_genres)} концертов без жанров:")
            for concert in concerts_without_genres[:5]:  # Показываем первые 5
                print(f"   Концерт {concert.id}: {concert.name}")
            if len(concerts_without_genres) > 5:
                print(f"   ... и еще {len(concerts_without_genres) - 5} концертов")
        else:
            print("✅ Все концерты имеют жанры")
        
        # 6. Статистика по жанрам
        genres_stats = session.exec(
            select(
                Genre.name,
                func.count(ConcertGenreLink.concert_id).label('concerts_count')
            )
            .outerjoin(ConcertGenreLink, Genre.id == ConcertGenreLink.genre_id)
            .group_by(Genre.id, Genre.name)
            .order_by(func.count(ConcertGenreLink.concert_id).desc())
        ).all()
        
        print(f"\n📊 Статистика по жанрам:")
        total_performances = 0
        for genre_name, concerts_count in genres_stats:
            print(f"   {genre_name}: {concerts_count} концертов")
            total_performances += concerts_count
        
        print(f"\n📊 Итого выступлений: {total_performances}")
        
        # 7. Проверяем несоответствие
        if total_links != total_performances:
            print(f"⚠️  Несоответствие: total_links ({total_links}) != total_performances ({total_performances})")
        else:
            print(f"✅ Данные согласованы: {total_links} = {total_performances}")
        
        # 8. Проверяем, есть ли концерты с несколькими жанрами в исходных данных
        concerts_with_multiple_genres = session.exec(
            select(Concert.id, Concert.name, Concert.genre)
            .where(Concert.genre.contains(','))
        ).all()
        
        if concerts_with_multiple_genres:
            print(f"\n⚠️  Найдено {len(concerts_with_multiple_genres)} концертов с составными жанрами:")
            for concert in concerts_with_multiple_genres[:5]:
                print(f"   Концерт {concert.id}: {concert.name} -> {concert.genre}")
            if len(concerts_with_multiple_genres) > 5:
                print(f"   ... и еще {len(concerts_with_multiple_genres) - 5} концертов")
        else:
            print("\n✅ Все концерты имеют простые жанры (без запятых)")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке данных: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_genre_data() 