#!/usr/bin/env python3
"""
Скрипт для пересоздания жанров с новой логикой (без разбивки по запятым)
"""

from database.database import get_session
from models import Concert, Genre, ConcertGenreLink
from sqlmodel import select, delete
from sqlalchemy import func

def recreate_genres():
    """Пересоздает жанры с новой логикой"""
    session = next(get_session())
    
    try:
        print("🗑️  Удаляем существующие связи жанр-концерт...")
        # Удаляем все существующие связи
        session.exec(delete(ConcertGenreLink))
        session.commit()
        
        print("🗑️  Удаляем существующие жанры...")
        # Удаляем все существующие жанры
        session.exec(delete(Genre))
        session.commit()
        
        print("🔄 Пересоздаем жанры с новой логикой...")
        
        # Получаем все концерты
        concerts = session.exec(select(Concert)).all()
        
        # Собираем уникальные жанры (как единое целое)
        unique_genres = set()
        for concert in concerts:
            if concert.genre:
                unique_genres.add(concert.genre.strip())
        
        print(f"📊 Найдено {len(unique_genres)} уникальных жанров:")
        for genre_name in sorted(unique_genres):
            print(f"  - {genre_name}")
        
        # Создаем жанры в базе данных
        genre_map = {}
        for genre_name in unique_genres:
            new_genre = Genre(name=genre_name)
            session.add(new_genre)
            session.commit()
            session.refresh(new_genre)
            genre_map[genre_name] = new_genre
            print(f"✅ Создан жанр '{genre_name}' (ID: {new_genre.id})")
        
        # Связываем концерты с жанрами
        links_created = 0
        for concert in concerts:
            if concert.genre:
                genre_name = concert.genre.strip()
                
                if genre_name in genre_map:
                    genre = genre_map[genre_name]
                    
                    # Создаем связь
                    link = ConcertGenreLink(
                        concert_id=concert.id,
                        genre_id=genre.id
                    )
                    session.add(link)
                    links_created += 1
        
        session.commit()
        print(f"\n✅ Создано {links_created} связей концерт-концерт")
        
        # Проверяем результат
        total_concerts = len(concerts)
        total_links = session.exec(select(func.count(ConcertGenreLink.concert_id))).first()
        
        print(f"\n📊 Итоговая статистика:")
        print(f"  • Всего концертов: {total_concerts}")
        print(f"  • Всего связей жанр-концерт: {total_links}")
        print(f"  • Всего жанров: {len(genre_map)}")
        
        if total_concerts == total_links:
            print("✅ Успех! Каждый концерт имеет ровно один жанр")
        else:
            print(f"⚠️  Внимание: {total_concerts} концертов, но {total_links} связей")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("🎵 Пересоздание жанров...")
    success = recreate_genres()
    if success:
        print("✅ Готово!")
    else:
        print("❌ Ошибка при пересоздании жанров") 