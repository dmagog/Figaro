from sqlmodel import SQLModel, Session, create_engine 
from contextlib import contextmanager
from .config import get_settings
import pandas as pd

engine = create_engine(url=get_settings().DATABASE_URL_psycopg, 
                       echo=True, pool_size=5, max_overflow=10)

def get_session():
    with Session(engine) as session:
        yield session
        
def init_db(demostart = None):
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # #Если инициализация базы происходит с созданием демо параметров
    # if demostart:
    #     create_demo_user(Session(engine)) # Создадим демо юзеров
    #     create_demo_operations_list(Session(engine)) # Прогоним случайные операции оплаты-пополнения
    #     create_demo_model(Session(engine))  #создадим тестовые модели
