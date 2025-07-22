from sqlmodel import SQLModel, Session, create_engine 
from contextlib import contextmanager
from .config import get_settings
from config_data_path import HALLS_LIST_PATH, CONCERTS_PATH, ARTISTS_PATH, PROGRAMM_PATH, TRANSACTIONS_PATH, ROUTES_PATH, OFF_PROGRAM_PATH, HALLS_TRANSITIONS_PATH
import pandas as pd

from services.crud import data_loader, user, festival, route_service

engine = create_engine(url=get_settings().DATABASE_URL_psycopg, 
                       echo=False, pool_size=5, max_overflow=10)  # Отключили SQL логирование для производительности

def get_session():
    with Session(engine) as session:
        yield session
        
def init_db(demostart = None):
    # Если инициализация базы происходит с созданием демо параметров
    if demostart:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

        with Session(engine) as session:
                print("\nЗагружаем данные из Excel файлов...")
                
                # Загружаем все Excel файлы в память
                halls_df = pd.read_excel(HALLS_LIST_PATH)
                concerts_df = pd.read_excel(CONCERTS_PATH)
                artists_df = pd.read_excel(ARTISTS_PATH)
                compositions_df = pd.read_excel(PROGRAMM_PATH)
                purchases_df = pd.read_excel(TRANSACTIONS_PATH)
                
                # Загружаем Офф-программу
                try:
                    off_program_df = pd.read_excel(OFF_PROGRAM_PATH)
                    print(f"  - Офф-программа: {len(off_program_df)} записей")
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки Офф-программы: {e}")
                    off_program_df = None
                
                # Загружаем данные о переходах между залами
                try:
                    hall_transitions_df = pd.read_excel(HALLS_TRANSITIONS_PATH)
                    print(f"  - Переходы между залами: матрица {hall_transitions_df.shape}")
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки переходов между залами: {e}")
                    hall_transitions_df = None
                
                print(f"Загружено файлов:")
                print(f"  - Залы: {len(halls_df)} записей")
                print(f"  - Концерты: {len(concerts_df)} записей")
                print(f"  - Артисты: {len(artists_df)} записей")
                print(f"  - Композиции: {len(compositions_df)} записей")
                print(f"  - Покупки: {len(purchases_df)} записей")
                
                # Используем оптимизированную функцию загрузки
                data_loader.load_all_data(
                    session=session,
                    df_halls=halls_df,
                    df_concerts=concerts_df,
                    df_artists=artists_df,
                    df_details=compositions_df,
                    df_ops=purchases_df,
                    df_off_program=off_program_df,
                    df_hall_transitions=hall_transitions_df,
                    disable_fk_checks=True  # Ускоряем загрузку
                )

                print("\n✅ Data loading complete.")

                print("Generating festival days...")
                festival.generate_festival_days(session)

                print("Creating default users...")
                user.create_default_users(session)
                print("\n✅ Default users created.")

                print("\nЗагружаем маршруты...")
                data_loader.load_routes_from_csv(session, ROUTES_PATH)
                print("\n✅ Загрузка маршрутов завершена.")

                # Обновляем кэш количества маршрутов
                from services.crud.data_loader import update_routes_count_cache
                update_routes_count_cache(session)
                print("✅ Кэш количества маршрутов обновлён.")

                # Инициализируем AvailableRoute
                print("Инициализируем AvailableRoute...")
                stats = route_service.init_available_routes(session)
                print(f"✅ AvailableRoute инициализированы: {stats['available_routes']} доступных из {stats['total_routes']} маршрутов")
                
                # Инициализируем кэш концертов в продаже, если его нет
                try:
                    route_service.init_available_concerts_cache(session)
                except Exception as e:
                    print(f"⚠️ Ошибка при инициализации кэша концертов: {e}")

                # Жанры теперь создаются автоматически в data_loader.load_all_data()
                print("✅ Жанры созданы автоматически при загрузке данных")

    else:
        # Инициализируем кэш количества маршрутов, если его нет
        with Session(engine) as session:
            from services.crud.data_loader import init_routes_count_cache
            init_routes_count_cache(session)
            
            # Проверяем и инициализируем AvailableRoute, если нужно
            try:
                route_service.ensure_available_routes_exist(session)
            except Exception as e:
                print(f"⚠️ Ошибка при инициализации AvailableRoute: {e}")
            
            # Инициализируем кэш концертов в продаже, если его нет
            try:
                route_service.init_available_concerts_cache(session)
            except Exception as e:
                print(f"⚠️ Ошибка при инициализации кэша концертов: {e}")
