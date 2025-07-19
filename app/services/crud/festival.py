# services/crud/festival.py
from sqlmodel import Session, select
from models import Concert, FestivalDay, Genre, ConcertGenreLink
import pandas as pd
from datetime import date
from sqlalchemy import func


def get_genres_with_concerts(session: Session):
    """Получает все жанры с информацией о концертах"""
    # Получаем жанры с количеством концертов
    genres_query = session.exec(
        select(Genre).order_by(Genre.name)
    ).all()
    
    genres_data = []
    for genre in genres_query:
        # Получаем количество концертов для жанра
        concerts_count = session.exec(
            select(func.count(ConcertGenreLink.concert_id))
            .where(ConcertGenreLink.genre_id == genre.id)
        ).first() or 0
        
        # Получаем данные о концертах для жанра
        concert_links = session.exec(
            select(ConcertGenreLink.concert_id)
            .where(ConcertGenreLink.genre_id == genre.id)
        ).all()
        
        concert_data = []
        if concert_links:
            concert_ids = [link for link in concert_links]
            concerts = session.exec(
                select(Concert.id, Concert.datetime)
                .where(Concert.id.in_(concert_ids))
                .order_by(Concert.datetime)
            ).all()
            concert_data = [(concert.id, concert.datetime) for concert in concerts]
        
        genres_data.append({
            'id': genre.id,
            'name': genre.name,
            'description': genre.description,
            'concerts_count': concerts_count,
            'concert_data': concert_data
        })
    
    return genres_data


def get_genres_summary(session: Session):
    """Получает сводную статистику по жанрам"""
    # Общее количество жанров
    total_genres = session.exec(select(func.count(Genre.id))).first() or 0
    
    # Количество жанров с концертами
    genres_with_concerts = session.exec(
        select(func.count(func.distinct(ConcertGenreLink.genre_id)))
    ).first() or 0
    
    # Общее количество выступлений (связей жанр-концерт)
    total_performances = session.exec(
        select(func.count(ConcertGenreLink.concert_id))
    ).first() or 0
    
    return {
        'total_genres': total_genres,
        'genres_with_concerts': genres_with_concerts,
        'total_performances': total_performances
    }


def generate_festival_days(session: Session):
    print("Формируем параметры фестиваля...")
    
    # Получаем все концерты одним запросом
    concerts = session.exec(select(Concert)).all()
    print(f"Найдено {len(concerts)} концертов для обработки")
    
    if not concerts:
        print("⚠️ Нет концертов для создания дней фестиваля")
        return
    
    # Получаем существующие дни фестиваля одним запросом
    existing_days = session.exec(select(FestivalDay.day)).all()
    existing_days_set = set(existing_days)
    print(f"Найдено {len(existing_days_set)} существующих дней фестиваля")
    
    # Группируем концерты по дням в памяти с оптимизированными вычислениями
    days_data = {}
    for concert in concerts:
        concert_date = concert.datetime.date()
        if concert_date not in days_data:
            days_data[concert_date] = {
                'start_times': [],
                'end_times': [],
                'tickets_count': 0,
                'total_concerts': 0
            }
        
        data = days_data[concert_date]
        data['start_times'].append(concert.datetime.time())
        data['end_times'].append((concert.datetime + concert.duration).time())
        data['total_concerts'] += 1
        if concert.tickets_available:
            data['tickets_count'] += 1
    
    # Создаем новые дни фестиваля
    created_days = 0
    skipped_days = 0
    
    for day_date, data in days_data.items():
        if day_date in existing_days_set:
            skipped_days += 1
            print(f"⏭️ День фестиваля {day_date} уже существует, пропускаем")
            continue
            
        # Оптимизированные вычисления времени
        first_concert = min(data['start_times'])
        last_concert = max(data['start_times'])
        end_of_last = max(data['end_times'])
        
        festival_day = FestivalDay(
            day=day_date,
            first_concert_time=first_concert,
            last_concert_time=last_concert,
            end_of_last_concert=end_of_last,
            concert_count=data['total_concerts'],
            available_concerts=data['tickets_count']
        )
        session.add(festival_day)
        created_days += 1
        print(f"✅ Создан день фестиваля: {day_date} ({data['total_concerts']} концертов)")
    
    # Сохраняем все изменения одним коммитом
    if created_days > 0:
        session.commit()
        print(f"💾 Сохранено {created_days} новых дней фестиваля")
    
    # Итоговая статистика без дополнительного запроса
    total_days_in_db = len(existing_days_set) + created_days
    print(f"📊 Статистика генерации дней фестиваля:")
    print(f"   • Создано новых дней: {created_days}")
    print(f"   • Пропущено существующих: {skipped_days}")
    print(f"   • Всего дней в базе: {total_days_in_db}")
    
    if created_days > 0:
        print("✅ Генерация дней фестиваля завершена успешно")
    else:
        print("ℹ️ Все дни фестиваля уже существуют в базе")
