# data_loader.py
from sqlmodel import Session, select
from models import Hall, Concert, Artist, Author, Composition, ConcertArtistLink, ConcertCompositionLink, Purchase
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List
import logging
import csv
from sqlmodel import Session
from models.route import Route
from sqlalchemy import and_, or_, text
import re

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для батчинга
import os
BATCH_SIZE = int(os.getenv('DATA_LOADER_BATCH_SIZE', '1000'))

# Функция для отключения/включения внешних ключей (для PostgreSQL)
def disable_foreign_keys(session):
    """Отключает проверку внешних ключей для ускорения загрузки"""
    try:
        session.exec(text("SET session_replication_role = replica;"))
        session.commit()
    except Exception as e:
        logger.warning(f"Не удалось отключить внешние ключи: {e}")

def enable_foreign_keys(session):
    """Включает проверку внешних ключей"""
    try:
        session.exec(text("SET session_replication_role = DEFAULT;"))
        session.commit()
    except Exception as e:
        logger.warning(f"Не удалось включить внешние ключи: {e}")


def get_or_create(session, model, **kwargs):
    instance = session.exec(select(model).filter_by(**kwargs)).first()
    if instance:
        return instance
    instance = model(**kwargs)
    session.add(instance)
    session.commit()
    session.refresh(instance)
    return instance


def bulk_get_or_create(session, model, records: List[Dict], unique_fields: List[str]):
    """Массовое создание записей с проверкой на существование"""
    if not records:
        return {}
    
    # Создаем уникальные ключи для поиска
    unique_keys = set()
    for record in records:
        key = tuple(record[field] for field in unique_fields if field in record)
        unique_keys.add(key)
    
    # Ищем все существующие записи одним запросом
    existing_map = {}
    if unique_keys:
        # Создаем OR условие для всех уникальных ключей
        conditions = []
        for key in unique_keys:
            key_dict = dict(zip(unique_fields, key))
            subconds = [(getattr(model, field) == value) for field, value in key_dict.items()]
            if subconds:
                condition = and_(*subconds)
                conditions.append(condition)
        # Выполняем один запрос для всех записей через OR
        if conditions:
            query = select(model).where(or_(*conditions))
            existing_records = session.exec(query).all()
            for record in existing_records:
                key = tuple(getattr(record, field) for field in unique_fields)
                existing_map[key] = record
    
    # Создаем новые записи
    new_records = []
    for record in records:
        key = tuple(record[field] for field in unique_fields if field in record)
        if key not in existing_map:
            new_records.append(record)
    
    if new_records:
        # Bulk insert для новых записей
        session.add_all([model(**record) for record in new_records])
        session.commit()
        
        # Обновляем карту существующих записей для новых записей
        for record in new_records:
            key = tuple(record[field] for field in unique_fields if field in record)
            instance = session.exec(
                select(model).where(
                    *[getattr(model, field) == record[field] for field in unique_fields if field in record]
                )
            ).first()
            existing_map[key] = instance
    
    return existing_map


def load_halls(session: Session, df_halls: pd.DataFrame):
    logger.info(f"Загружаем {len(df_halls)} залов из Excel")
    
    records = []
    for _, row in df_halls.iterrows():
        records.append({
            "name": row["HallName"],
            "concert_count": row.get("count", 0),
            "address": None if pd.isna(row.get("Adress")) else row.get("Adress"),
            "latitude": None if pd.isna(row.get("Lat")) else row.get("Lat"),
            "longitude": None if pd.isna(row.get("Lon")) else row.get("Lon"),
            "seats": 0 if pd.isna(row.get("Seats")) else row.get("Seats"),
        })
    
    bulk_get_or_create(session, Hall, records, ["name"])
    
    count = session.exec(select(Hall)).all()
    logger.info(f"В базе теперь {len(count)} залов")


def load_concerts(session: Session, df_concerts: pd.DataFrame):
    logger.info(f"Загружаем {len(df_concerts)} концертов из Excel")
    
    # Сначала загружаем все залы в память для быстрого доступа
    halls = {hall.name: hall.id for hall in session.exec(select(Hall)).all()}
    
    records = []
    for _, row in df_concerts.iterrows():
        hall_id = halls.get(row["HallName"])
        if not hall_id:
            logger.warning(f"Зал {row['HallName']} не найден, пропускаем концерт {row['ShowId']}")
            continue
            
        records.append({
            "external_id": row["ShowId"],
            "name": row["ShowName"],
            "datetime": pd.to_datetime(row["ShowDate"]),
            "duration": pd.to_timedelta(row["ShowLong"]),
            "genre": None if pd.isna(row.get("Genre")) else row.get("Genre"),
            "price": None if pd.isna(row.get("Price")) else row.get("Price"),
            "is_family_friendly": bool(row.get("Family", False)),
            "tickets_available": bool(row.get("Tickets", False)),
            "link": None if pd.isna(row.get("link")) else row.get("link"),
            "hall_id": hall_id,
        })
    
    bulk_get_or_create(session, Concert, records, ["external_id"])
    
    count = session.exec(select(Concert)).all()
    logger.info(f"В базе теперь {len(count)} концертов")


def load_artists(session: Session, df_artists: pd.DataFrame):
    logger.info(f"Загружаем {len(df_artists.drop_duplicates(['ShowNum', 'Artists']))} артистов из Excel")
    
    # Загружаем концерты в память
    concerts = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
    
    # Группируем артистов по концертам
    artist_records = []
    link_records = []
    
    for _, row in df_artists.drop_duplicates(["ShowNum", "Artists"]).iterrows():
        artist_records.append({
            "name": row["Artists"],
            "is_special": bool(row.get("Spetial", False))
        })
        
        concert_id = concerts.get(row["ShowNum"])
        if concert_id:
            link_records.append({
                "concert_id": concert_id,
                "artist_name": row["Artists"]  # Временное поле для связи
            })
    
    # Создаем артистов
    artists_map = bulk_get_or_create(session, Artist, artist_records, ["name"])
    
    # Создаем связи
    for link_record in link_records:
        artist_name = link_record.pop("artist_name")
        artist = session.exec(select(Artist).where(Artist.name == artist_name)).first()
        if artist:
            get_or_create(
                session,
                ConcertArtistLink,
                concert_id=link_record["concert_id"],
                artist_id=artist.id
            )
    
    count = session.exec(select(Artist)).all()
    logger.info(f"В базе теперь {len(count)} артистов")


def load_compositions(session: Session, df_details: pd.DataFrame):
    logger.info(f"Загружаем {len(df_details.drop_duplicates(['ShowNum', 'Author', 'Programm']))} композиций из Excel")
    
    # Загружаем концерты в память
    concerts = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
    
    # Группируем композиции
    author_records = []
    composition_records = []
    link_records = []
    
    for _, row in df_details.drop_duplicates(["ShowNum", "Author", "Programm"]).iterrows():
        author_records.append({"name": row["Author"]})
        
        composition_records.append({
            "name": row["Programm"],
            "author_name": row["Author"]  # Временное поле для связи
        })
        
        concert_id = concerts.get(row["ShowNum"])
        if concert_id:
            link_records.append({
                "concert_id": concert_id,
                "composition_name": row["Programm"],
                "author_name": row["Author"]
            })
    
    # Создаем авторов
    authors_map = bulk_get_or_create(session, Author, author_records, ["name"])
    
    # Создаем композиции
    for comp_record in composition_records:
        author_name = comp_record.pop("author_name")
        author = session.exec(select(Author).where(Author.name == author_name)).first()
        if author:
            comp_record["author_id"] = author.id
            get_or_create(session, Composition, **comp_record)
    
    # Создаем связи
    for link_record in link_records:
        composition = session.exec(
            select(Composition)
            .join(Author)
            .where(
                Composition.name == link_record["composition_name"],
                Author.name == link_record["author_name"]
            )
        ).first()
        
        if composition:
            get_or_create(
                session,
                ConcertCompositionLink,
                concert_id=link_record["concert_id"],
                composition_id=composition.id
            )

    count = session.exec(select(Composition)).all()
    logger.info(f"В базе теперь {len(count)} композиций")


def load_purchases(session: Session, df_ops: pd.DataFrame):
    logger.info(f"Загружаем {len(df_ops.drop_duplicates(['OpId']))} покупок из Excel")
    
    # Загружаем концерты в память
    concerts = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
    
    # Группируем покупки по батчам
    total_records = len(df_ops.drop_duplicates(["OpId"]))
    processed = 0
    
    for batch_start in range(0, total_records, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_records)
        batch_df = df_ops.drop_duplicates(["OpId"]).iloc[batch_start:batch_end]
        
        records = []
        for _, row in batch_df.iterrows():
            concert_id = concerts.get(row["ShowId"])
            if not concert_id:
                logger.warning(f"Концерт {row['ShowId']} не найден, пропускаем покупку {row['OpId']}")
                continue
                
            records.append({
                "external_op_id": row["OpId"],
                "user_external_id": str(row["ClientId"]),
                "concert_id": concert_id,
                "purchased_at": pd.to_datetime(row["OpDate"]),
                "price": None if pd.isna(row.get("Price")) else row.get("Price")
            })
        
        if records:
            bulk_get_or_create(session, Purchase, records, ["external_op_id"])
        
        processed += len(records)
        logger.info(f"Обработано {processed}/{total_records} покупок ({processed/total_records*100:.1f}%)")
    
    count = session.exec(select(Purchase)).all()
    logger.info(f"В базе теперь {len(count)} покупок")


def load_all_data(session: Session, df_halls: pd.DataFrame, df_concerts: pd.DataFrame, 
                  df_artists: pd.DataFrame, df_details: pd.DataFrame, df_ops: pd.DataFrame,
                  disable_fk_checks: bool = True):
    """
    Загружает все данные с оптимизациями для больших файлов
    
    Args:
        session: Сессия базы данных
        df_halls: DataFrame с залами
        df_concerts: DataFrame с концертами
        df_artists: DataFrame с артистами
        df_details: DataFrame с деталями программ
        df_ops: DataFrame с покупками
        disable_fk_checks: Отключить проверку внешних ключей для ускорения
    """
    logger.info("Начинаем загрузку всех данных...")
    
    if disable_fk_checks:
        logger.info("Отключаем проверку внешних ключей для ускорения загрузки")
        disable_foreign_keys(session)
    
    try:
        # Загружаем данные в правильном порядке (зависимости)
        load_halls(session, df_halls)
        load_concerts(session, df_concerts)
        load_artists(session, df_artists)
        load_compositions(session, df_details)
        load_purchases(session, df_ops)
        
        logger.info("Загрузка всех данных завершена успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных: {e}")
        raise
    finally:
        if disable_fk_checks:
            logger.info("Включаем проверку внешних ключей")
            enable_foreign_keys(session)


def load_routes_from_csv(session: Session, path: str, batch_size: int = 1000, status_dict=None):
    import os
    import logging
    logger = logging.getLogger(__name__)
    if not os.path.exists(path):
        logger.warning(f"[load_routes_from_csv] Файл {path} не найден — пропускаем загрузку маршрутов.")
        if status_dict is not None:
            status_dict["error"] = f"Файл {path} не найден"
            status_dict["in_progress"] = False
        return {"added": 0, "updated": 0, "skipped": 0}
    added, updated, skipped = 0, 0, 0
    # Считаем общее количество строк для прогресса
    with open(path, newline='', encoding='utf-8') as csvfile:
        import csv
        total_lines = sum(1 for _ in csvfile) - 1  # -1 для заголовка
    if status_dict is not None:
        status_dict["total"] = total_lines
        status_dict["progress"] = 0
        status_dict["added"] = 0
        status_dict["updated"] = 0
        status_dict["error"] = None
    with open(path, newline='', encoding='utf-8') as csvfile:
        import csv
        reader = csv.DictReader(csvfile)
        batch = []
        for i, row in enumerate(reader, 1):
            sostav_raw = row.get('Sostav', '')
            concerts_list = re.findall(r'\d+', sostav_raw)
            concerts_sorted = ','.join(sorted(concerts_list, key=str))
            existing_route = session.exec(select(Route).where(Route.Sostav == concerts_sorted)).first()
            if existing_route:
                for field in Route.__fields__:
                    if field == 'id' or field == 'Sostav':
                        continue
                    value = row.get(field)
                    if value is not None:
                        field_type = Route.__fields__[field].annotation if hasattr(Route, '__fields__') else None
                        if field_type in [int, float]:
                            try:
                                value = field_type(value)
                            except Exception:
                                pass
                        setattr(existing_route, field, value)
                session.add(existing_route)
                updated += 1
            else:
                route_kwargs = {k: v for k, v in row.items()}
                route_kwargs['Sostav'] = concerts_sorted
                for field in Route.__fields__:
                    if field in route_kwargs and route_kwargs[field] is not None:
                        field_type = Route.__fields__[field].annotation if hasattr(Route, '__fields__') else None
                        if field_type in [int, float]:
                            try:
                                route_kwargs[field] = field_type(route_kwargs[field])
                            except Exception:
                                pass
                route = Route(**route_kwargs)
                batch.append(route)
            if len(batch) >= batch_size:
                session.add_all(batch)
                session.commit()
                added += len(batch)
                batch = []
            # Логируем прогресс каждые 1000 строк
            if i % 1000 == 0 or i == total_lines:
                percent = (i / total_lines) * 100 if total_lines > 0 else 100
                logger.info(f"Обработано {i}/{total_lines} маршрутов ({percent:.1f}%)")
                if status_dict is not None:
                    status_dict["progress"] = i
                    status_dict["added"] = added
                    status_dict["updated"] = updated
        if batch:
            session.add_all(batch)
            session.commit()
            added += len(batch)
        session.commit()
    if status_dict is not None:
        status_dict["progress"] = total_lines
        status_dict["added"] = added
        status_dict["updated"] = updated
        status_dict["in_progress"] = False
    logger.info(f"[load_routes_from_csv] Загружено маршрутов: добавлено {added}, обновлено {updated}")
    return {"added": added, "updated": updated, "skipped": skipped}