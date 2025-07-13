from sqlmodel import SQLModel, Session, create_engine 
from contextlib import contextmanager
from .config import get_settings
from config_data_path import HALLS_LIST_PATH, CONCERTS_PATH, ARTISTS_PATH, PROGRAMM_PATH, TRANSACTIONS_PATH
import pandas as pd

from services.crud import data_loader, user

engine = create_engine(url=get_settings().DATABASE_URL_psycopg, 
                       echo=True, pool_size=5, max_overflow=10)

def get_session():
    with Session(engine) as session:
        yield session
        
def init_db(demostart = None):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        print("\nLoading halls...")
        halls_df = pd.read_excel(HALLS_LIST_PATH)
        data_loader.load_halls(session, halls_df)

        print("Loading concerts...")
        concerts_df = pd.read_excel(CONCERTS_PATH)
        data_loader.load_concerts(session, concerts_df)

        print("Loading artists...")
        artists_df = pd.read_excel(ARTISTS_PATH)
        data_loader.load_artists(session, artists_df)

        print("Loading compositions...")
        compositions_df = pd.read_excel(PROGRAMM_PATH)
        data_loader.load_compositions(session, compositions_df)

        print("Loading purchases...")
        purchases_df = pd.read_excel(TRANSACTIONS_PATH)
        data_loader.load_purchases(session, purchases_df)

        print("\n✅ Data loading complete.")


        print("Creating default users...")
        user.create_default_users(session)
        print("\n✅ Default users created.")


    # #Если инициализация базы происходит с созданием демо параметров
    # if demostart:
    #     create_demo_user(Session(engine)) # Создадим демо юзеров
    #     create_demo_operations_list(Session(engine)) # Прогоним случайные операции оплаты-пополнения
    #     create_demo_model(Session(engine))  #создадим тестовые модели
