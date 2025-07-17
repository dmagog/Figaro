# data_loader.py
from sqlmodel import Session, select, delete
from models import Hall, HallTransition, Concert, Artist, Author, Composition, ConcertArtistLink, ConcertCompositionLink, Purchase, AvailableRoute, OffProgram, EventFormat
from models.statistics import Statistics
from datetime import datetime, timedelta, timezone
import pandas as pd
from typing import Dict, List
import logging
import csv
from sqlmodel import Session
from models.route import Route
from sqlalchemy import and_, or_, text
import re
from . import route_service

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
    halls = {hall.name: hall for hall in session.exec(select(Hall)).all()}
    
    records = []
    for _, row in df_concerts.iterrows():
        hall = halls.get(row["HallName"])
        if not hall:
            logger.warning(f"Зал {row['HallName']} не найден, пропускаем концерт {row['ShowId']}")
            continue
            
        # Инициализируем tickets_left количеством мест в зале, если не передано конкретное значение
        tickets_left = None
        if not pd.isna(row.get("TicketsLeft")):
            tickets_left = int(row.get("TicketsLeft"))
        elif hall.seats > 0:
            tickets_left = hall.seats
            
        records.append({
            "external_id": row["ShowId"],
            "name": row["ShowName"],
            "datetime": pd.to_datetime(row["ShowDate"]),
            "duration": pd.to_timedelta(row["ShowLong"]),
            "genre": None if pd.isna(row.get("Genre")) else row.get("Genre"),
            "price": None if pd.isna(row.get("Price")) else row.get("Price"),
            "is_family_friendly": bool(row.get("Family", False)),
            "tickets_available": bool(row.get("Tickets", False)),
            "tickets_left": tickets_left,
            "link": None if pd.isna(row.get("link")) else row.get("link"),
            "hall_id": hall.id,
        })
    
    bulk_get_or_create(session, Concert, records, ["external_id"])
    
    count = session.exec(select(Concert)).all()
    logger.info(f"В базе теперь {len(count)} концертов")


def load_artists(session: Session, df_artists: pd.DataFrame):
    logger.info(f"Загружаем артистов из Excel")
    
    # Загружаем концерты в память
    concerts = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
    
    # Сначала создаем уникальных артистов
    unique_artists = df_artists["Artists"].dropna().unique()
    logger.info(f"Найдено {len(unique_artists)} уникальных артистов")
    
    # Создаем записи артистов с учетом флага is_special
    artist_records = []
    for artist_name in unique_artists:
        # Находим все записи для этого артиста, чтобы определить is_special
        artist_rows = df_artists[df_artists["Artists"] == artist_name]
        is_special = any(artist_rows.get("Spetial", False))
    
        artist_records.append({
            "name": artist_name,
            "is_special": is_special
            })
    
    # Создаем артистов
    artists_map = bulk_get_or_create(session, Artist, artist_records, ["name"])
    
    # Создаем словарь артистов для быстрого доступа
    artists_dict = {artist.name: artist for artist in session.exec(select(Artist)).all()}
    
    # Создаем связи с концертами
    for _, row in df_artists.drop_duplicates(["ShowNum", "Artists"]).iterrows():
        concert_id = concerts.get(row["ShowNum"])
        if concert_id:
            artist_name = row["Artists"]
            artist = artists_dict.get(artist_name)
            
        if artist:
            get_or_create(
                session,
                ConcertArtistLink,
                concert_id=concert_id,
                artist_id=artist.id
            )
    
    count = session.exec(select(Artist)).all()
    logger.info(f"В базе теперь {len(count)} артистов")


def load_compositions(session: Session, df_details: pd.DataFrame):
    logger.info(f"Загружаем композиции из Excel")
    
    # Загружаем концерты в память
    concerts = {concert.external_id: concert.id for concert in session.exec(select(Concert)).all()}
    
    # Сначала создаем уникальных авторов
    unique_authors = df_details["Author"].dropna().unique()
    logger.info(f"Найдено {len(unique_authors)} уникальных авторов")
    
    author_records = []
    for author_name in unique_authors:
        author_records.append({"name": author_name})
    
    # Создаем авторов
    authors_map = bulk_get_or_create(session, Author, author_records, ["name"])
    
    # Создаем словарь авторов для быстрого доступа
    authors_dict = {author.name: author for author in session.exec(select(Author)).all()}
    
    # Группируем композиции по уникальным сочетаниям (Author, Programm)
    composition_records = []
    link_records = []
    
    for _, row in df_details.drop_duplicates(["Author", "Programm"]).iterrows():
        author_name = row["Author"]
        author = authors_dict.get(author_name)
        
        if author:
            composition_records.append({
                "name": row["Programm"],
                "author_id": author.id
            })
    
    # Создаем композиции
    for comp_record in composition_records:
        get_or_create(session, Composition, **comp_record)
    
    # Создаем связи с концертами
    for _, row in df_details.drop_duplicates(["ShowNum", "Author", "Programm"]).iterrows():
        concert_id = concerts.get(row["ShowNum"])
        if concert_id:
            author_name = row["Author"]
            composition_name = row["Programm"]
            
        composition = session.exec(
            select(Composition)
            .join(Author)
            .where(
                    Composition.name == composition_name,
                    Author.name == author_name
            )
        ).first()
        
        if composition:
            get_or_create(
                session,
                ConcertCompositionLink,
                concert_id=concert_id,
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


def update_customer_route_matches(session: Session):
    """
    Обновляет сопоставления покупателей с маршрутами.
    Эта функция должна вызываться после загрузки маршрутов.
    """
    from models import CustomerRouteMatch
    from datetime import datetime
    from collections import defaultdict
    
    logger.info("Начинаем обновление сопоставлений покупателей с маршрутами...")
    
    # Получаем все маршруты
    all_routes = session.exec(select(Route)).all()
    logger.info(f"Загружено {len(all_routes)} маршрутов")
    
    # Создаем оптимизированные индексы маршрутов
    routes_by_composition = {}
    routes_by_length = defaultdict(list)  # Группируем маршруты по длине
    routes_by_concerts = defaultdict(list)  # Индекс по отдельным концертам
    
    for route in all_routes:
        try:
            route_concert_ids = tuple(sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()]))
            routes_by_composition[route_concert_ids] = route
            routes_by_length[len(route_concert_ids)].append((route_concert_ids, route))
            
            # Создаем индекс по отдельным концертам для быстрого поиска
            for concert_id in route_concert_ids:
                routes_by_concerts[concert_id].append((route_concert_ids, route))
        except (ValueError, AttributeError) as e:
            logger.warning(f"Ошибка при парсинге маршрута {route.id}: {e}")
            continue
    
    logger.info(f"Создано индексов: {len(routes_by_composition)} маршрутов, {len(routes_by_concerts)} уникальных концертов")
    
    # Получаем всех покупателей с их уникальными концертами
    from sqlalchemy import func
    customer_concerts = session.exec(
        select(
            Purchase.user_external_id,
            func.array_agg(func.distinct(Purchase.concert_id)).label('unique_concert_ids')
        )
        .group_by(Purchase.user_external_id)
    ).all()
    
    logger.info(f"Найдено {len(customer_concerts)} покупателей для сопоставления")
    
    # Очищаем старые сопоставления
    session.exec(delete(CustomerRouteMatch))
    session.commit()
    logger.info("Очищены старые сопоставления")
    
    # Батчинг для оптимизации
    BATCH_SIZE = 500
    match_records = []
    
    # Обрабатываем каждого покупателя
    processed = 0
    for customer_data in customer_concerts:
        external_id = str(customer_data[0])
        unique_concert_ids = customer_data[1] if customer_data[1] else []
        
        if not unique_concert_ids:
            # Создаем запись для покупателя без покупок
            match_record = CustomerRouteMatch(
                user_external_id=external_id,
                found=False,
                match_type="none",
                reason="У покупателя нет покупок",
                customer_concerts="",
                customer_concerts_count=0,
                total_routes_checked=len(all_routes),
                updated_at=datetime.utcnow()
            )
            match_records.append(match_record)
            processed += 1
            continue
        
        # Сортируем уникальные концерты
        customer_concert_ids = sorted(unique_concert_ids)
        customer_concert_ids_str = ",".join(map(str, customer_concert_ids))
        customer_concert_ids_tuple = tuple(customer_concert_ids)
        customer_concert_ids_set = set(customer_concert_ids)
        
        # Ищем точные совпадения
        exact_matches = []
        partial_matches = []
        
        # Проверяем точное совпадение (O(1) операция)
        if customer_concert_ids_tuple in routes_by_composition:
            route = routes_by_composition[customer_concert_ids_tuple]
            exact_matches.append({
                "route_id": route.id,
                "match_type": "exact",
                "match_percentage": 100.0
            })
        
        # Оптимизированный поиск частичных совпадений
        if not exact_matches:
            # Находим потенциальные маршруты по первому концерту
            potential_routes = []
            if customer_concert_ids:
                first_concert = customer_concert_ids[0]
                if first_concert in routes_by_concerts:
                    potential_routes.extend(routes_by_concerts[first_concert])
            
            # Проверяем только потенциальные маршруты
            for route_concert_ids_tuple, route in potential_routes:
                if customer_concert_ids_set.issubset(set(route_concert_ids_tuple)):
                    match_percentage = (len(customer_concert_ids) / len(route_concert_ids_tuple)) * 100
                    partial_matches.append({
                        "route_id": route.id,
                        "match_type": "partial",
                        "match_percentage": match_percentage
                    })
            
            # Сортируем частичные совпадения
            partial_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        
        # Определяем лучший маршрут
        best_match = None
        match_type = "none"
        reason = "Не найдено подходящих маршрутов"
        
        if exact_matches:
            best_match = exact_matches[0]
            match_type = "exact"
            reason = None
        elif partial_matches:
            best_match = partial_matches[0]
            match_type = "partial"
            reason = None
        
        # Создаем запись
        match_record = CustomerRouteMatch(
            user_external_id=external_id,
            found=best_match is not None,
            match_type=match_type,
            reason=reason,
            customer_concerts=customer_concert_ids_str,
            customer_concerts_count=len(customer_concert_ids),
            best_route_id=best_match["route_id"] if best_match else None,
            match_percentage=best_match["match_percentage"] if best_match else None,
            total_routes_checked=len(all_routes),
            updated_at=datetime.utcnow()
        )
        
        match_records.append(match_record)
        processed += 1
        
        # Батчинг: сохраняем записи порциями
        if len(match_records) >= BATCH_SIZE:
            session.add_all(match_records)
            session.commit()
            logger.info(f"Обработано {processed}/{len(customer_concerts)} покупателей (батч сохранен)")
            match_records = []
        
        if processed % 1000 == 0:
            logger.info(f"Обработано {processed}/{len(customer_concerts)} покупателей")
    
    # Сохраняем оставшиеся записи
    if match_records:
        session.add_all(match_records)
        session.commit()
        logger.info(f"Сохранен финальный батч из {len(match_records)} записей")
    
    logger.info(f"Завершено обновление сопоставлений. Обработано {processed} покупателей")


def load_all_data(session: Session, df_halls: pd.DataFrame, df_concerts: pd.DataFrame, 
                  df_artists: pd.DataFrame, df_details: pd.DataFrame, df_ops: pd.DataFrame,
                  df_off_program: pd.DataFrame = None, df_hall_transitions: pd.DataFrame = None, 
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
        df_off_program: DataFrame с Офф-программой (опционально)
        df_hall_transitions: DataFrame с матрицей переходов между залами (опционально)
        disable_fk_checks: Отключить проверку внешних ключей для ускорения
    """
    logger.info("Начинаем загрузку всех данных...")
    
    if disable_fk_checks:
        logger.info("Отключаем проверку внешних ключей для ускорения загрузки")
        disable_foreign_keys(session)
    
    try:
        # Загружаем данные в правильном порядке (зависимости)
        load_halls(session, df_halls)
        
        # Загружаем данные о переходах между залами после залов (если переданы)
        if df_hall_transitions is not None:
            load_hall_transitions(session, df_hall_transitions)
        
        # Загружаем Офф-программу после залов (если передана)
        if df_off_program is not None:
            load_off_program(session, df_off_program)
        else:
            # Инициализируем кэш офф-программы даже если данные не загружаются
            init_off_program_count_cache(session)
        
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
        
        # Обновляем кэш количества маршрутов
        update_routes_count_cache(session)
        
        # Инициализируем или обновляем AvailableRoute
        logger.info("Обновляем AvailableRoute после загрузки маршрутов...")
        try:
            # Проверяем и инициализируем AvailableRoute (если нужно)
            was_initialized = route_service.ensure_available_routes_exist(session)
            
            # Получаем статистику
            stats = route_service.get_available_routes_stats(session)
            logger.info(f"AvailableRoute обновлены: {stats['available_routes']} доступных из {stats['total_routes']} маршрутов ({stats['availability_percentage']}%)")
            
            # Инициализируем кэши только если AvailableRoute не были созданы заново
            if not was_initialized:
                route_service.init_available_routes_cache(session)
                route_service.init_available_concerts_cache(session)
        except Exception as e:
            logger.error(f"Ошибка при обновлении AvailableRoute: {e}")
        
        # Обновляем сопоставления покупателей с маршрутами
        logger.info("Обновляем сопоставления покупателей с маршрутами...")
        try:
            update_customer_route_matches(session)
            logger.info("Сопоставления покупателей с маршрутами обновлены успешно")
        except Exception as e:
            logger.error(f"Ошибка при обновлении сопоставлений покупателей: {e}")
        
    if status_dict is not None:
        status_dict["progress"] = total_lines
        status_dict["added"] = added
        status_dict["updated"] = updated
        status_dict["in_progress"] = False
    logger.info(f"[load_routes_from_csv] Загружено маршрутов: добавлено {added}, обновлено {updated}")
    return {"added": added, "updated": updated, "skipped": skipped}


def update_routes_count_cache(session: Session):
    """Обновляет кэшированное количество маршрутов в таблице Statistics"""
    try:
        # Подсчитываем актуальное количество маршрутов
        routes = session.exec(select(Route)).all()
        routes_count = len(routes)
        
        # Ищем существующую запись или создаём новую
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "routes_count")
        ).first()
        
        if stats_record:
            stats_record.value = routes_count
            stats_record.updated_at = datetime.now(timezone.utc)
        else:
            stats_record = Statistics(
                key="routes_count",
                value=routes_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
        
        session.commit()
        logger.info(f"Кэш количества маршрутов обновлён: {routes_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении кэша количества маршрутов: {e}")
        session.rollback()


def init_routes_count_cache(session: Session):
    """Инициализирует кэш количества маршрутов, если его нет"""
    try:
        # Проверяем, есть ли уже запись в кэше
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "routes_count")
        ).first()
        
        if not stats_record:
            # Если кэша нет, создаём его
            update_routes_count_cache(session)
            logger.info("Кэш количества маршрутов инициализирован")
        else:
            logger.info("Кэш количества маршрутов уже существует")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации кэша количества маршрутов: {e}")
        session.rollback()


def load_off_program(session: Session, df_off_program: pd.DataFrame):
    """
    Загружает данные Офф-программы фестиваля
    
    Args:
        session: Сессия базы данных
        df_off_program: DataFrame с данными Офф-программы
    """
    logger.info(f"Загружаем {len(df_off_program)} мероприятий Офф-программы из Excel")
    
    records = []
    for _, row in df_off_program.iterrows():
        # Обрабатываем формат мероприятия
        format_value = None
        if not pd.isna(row.get("Format")):
            format_str = str(row.get("Format")).strip()
            try:
                format_value = EventFormat(format_str)
            except ValueError:
                logger.warning(f"Неизвестный формат мероприятия: {format_str}")
        
        # Обрабатываем продолжительность
        event_long = str(row.get("EventLong", "00:00:00"))
        if not event_long or event_long == "nan":
            event_long = "00:00:00"
        
        # Обрабатываем ссылку
        link_value = None
        if not pd.isna(row.get("link")):
            link_value = str(row.get("link")).strip()
            if link_value == "nan":
                link_value = None
        
        records.append({
            "event_num": int(row["EventNum"]),
            "event_name": str(row["EventName"]),
            "description": None if pd.isna(row.get("Description")) else str(row.get("Description")),
            "event_date": pd.to_datetime(row["EventDate"]),
            "event_long": event_long,
            "hall_name": str(row["HallName"]),
            "format": format_value,
            "recommend": bool(row.get("Recommend", False)),
            "link": link_value
        })
    
    # Используем bulk_get_or_create для эффективной загрузки
    bulk_get_or_create(session, OffProgram, records, ["event_num"])
    
    count = session.exec(select(OffProgram)).all()
    logger.info(f"В базе теперь {len(count)} мероприятий Офф-программы")
    
    # Обновляем статистику офф-программы
    update_off_program_count_cache(session)


def update_off_program_count_cache(session: Session):
    """Обновляет кэшированное количество мероприятий офф-программы в таблице Statistics"""
    try:
        # Подсчитываем актуальное количество мероприятий офф-программы
        off_program_events = session.exec(select(OffProgram)).all()
        off_program_count = len(off_program_events)
        
        # Ищем существующую запись или создаём новую
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "off_program_count")
        ).first()
        
        if stats_record:
            stats_record.value = off_program_count
            stats_record.updated_at = datetime.now(timezone.utc)
        else:
            stats_record = Statistics(
                key="off_program_count",
                value=off_program_count,
                updated_at=datetime.now(timezone.utc)
            )
            session.add(stats_record)
        
        session.commit()
        logger.info(f"Кэш количества мероприятий офф-программы обновлён: {off_program_count}")
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении кэша количества мероприятий офф-программы: {e}")
        session.rollback()


def init_off_program_count_cache(session: Session):
    """Инициализирует кэш количества мероприятий офф-программы, если его нет"""
    try:
        # Проверяем, есть ли уже запись в кэше
        stats_record = session.exec(
            select(Statistics).where(Statistics.key == "off_program_count")
        ).first()
        
        if not stats_record:
            # Если кэша нет, создаём его
            update_off_program_count_cache(session)
            logger.info("Кэш количества мероприятий офф-программы инициализирован")
        else:
            logger.info("Кэш количества мероприятий офф-программы уже существует")
            
    except Exception as e:
        logger.error(f"Ошибка при инициализации кэша количества мероприятий офф-программы: {e}")
        session.rollback()


def load_hall_transitions(session: Session, df_transitions: pd.DataFrame):
    """
    Загружает данные о времени переходов между залами
    
    Args:
        session: Сессия базы данных
        df_transitions: DataFrame с матрицей переходов между залами
    """
    logger.info(f"Загружаем данные о переходах между залами из матрицы {df_transitions.shape}")
    
    # Получаем все залы в память для быстрого доступа
    halls = {hall.name: hall for hall in session.exec(select(Hall)).all()}
    
    # Очищаем существующие данные о переходах
    session.exec(delete(HallTransition))
    session.commit()
    
    records = []
    transition_count = 0
    created_pairs = set()  # Для отслеживания уже созданных пар переходов
    
    # Обрабатываем матрицу переходов
    for _, row in df_transitions.iterrows():
        from_hall_name = row.iloc[0]  # Первая колонка содержит название зала отправления
        
        # Проверяем, что зал отправления существует
        from_hall = halls.get(from_hall_name)
        if not from_hall:
            logger.warning(f"Зал отправления '{from_hall_name}' не найден в базе данных")
            continue
        
        # Обрабатываем каждую колонку (кроме первой, которая содержит названия залов)
        for col_name, transition_time in row.iloc[1:].items():
            # Пропускаем пустые значения и NaN
            if pd.isna(transition_time) or transition_time == '':
                continue
            
            # Проверяем, что зал назначения существует
            to_hall = halls.get(col_name)
            if not to_hall:
                logger.warning(f"Зал назначения '{col_name}' не найден в базе данных")
                continue
            
            # Пропускаем переход к самому себе (диагональ матрицы)
            if from_hall.id == to_hall.id:
                continue
            
            # Преобразуем время перехода в целое число
            try:
                transition_time_int = int(transition_time)
            except (ValueError, TypeError):
                logger.warning(f"Некорректное значение времени перехода: {transition_time} для {from_hall_name} -> {col_name}")
                continue
            
            # Создаем пару переходов (в обоих направлениях)
            pair_key = tuple(sorted([from_hall.id, to_hall.id]))
            if pair_key not in created_pairs:
                # Прямой переход
                records.append({
                    "from_hall_id": from_hall.id,
                    "to_hall_id": to_hall.id,
                    "transition_time": transition_time_int
                })
                
                # Обратный переход (то же время)
                records.append({
                    "from_hall_id": to_hall.id,
                    "to_hall_id": from_hall.id,
                    "transition_time": transition_time_int
                })
                
                created_pairs.add(pair_key)
                transition_count += 2  # Добавляем 2 перехода
                
                logger.debug(f"Создан переход: {from_hall_name} ↔ {col_name} ({transition_time_int} мин)")
    
    # Массовое создание записей
    if records:
        session.add_all([HallTransition(**record) for record in records])
        session.commit()
    
    logger.info(f"Загружено {transition_count} записей о переходах между залами (включая обратные)")
    
    # Проверяем результат
    total_transitions = session.exec(select(HallTransition)).all()
    logger.info(f"В базе теперь {len(total_transitions)} записей о переходах между залами")