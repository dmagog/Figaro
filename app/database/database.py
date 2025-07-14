from sqlmodel import SQLModel, Session, create_engine 
from contextlib import contextmanager
from .config import get_settings
from config_data_path import HALLS_LIST_PATH, CONCERTS_PATH, ARTISTS_PATH, PROGRAMM_PATH, TRANSACTIONS_PATH, ROUTES_PATH
import pandas as pd

from services.crud import data_loader, user, festival

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


    # #Если инициализация базы происходит с созданием демо параметров
    # if demostart:
    #     create_demo_user(Session(engine)) # Создадим демо юзеров
    #     create_demo_operations_list(Session(engine)) # Прогоним случайные операции оплаты-пополнения
    #     create_demo_model(Session(engine))  #создадим тестовые модели
