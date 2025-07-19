import pytest
import sys
import os
from pathlib import Path

# Добавляем путь к приложению в Python path
app_path = Path(__file__).parent.parent
sys.path.insert(0, str(app_path))

# Устанавливаем переменные окружения для тестов
os.environ["TESTING"] = "True"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"  # Добавляем SECRET_KEY для тестов
os.environ["COOKIE_NAME"] = "access_token"  # Добавляем COOKIE_NAME для тестов

# Переопределяем функцию get_settings ДО импорта модулей
def override_get_settings():
    """Тестовая версия настроек"""
    from database.config import Settings
    
    class TestSettings(Settings):
        def validate(self) -> None:
            """Пропускаем валидацию для тестов"""
            pass
        
        @property
        def DATABASE_URL_psycopg(self):
            return "sqlite:///:memory:"
    
    return TestSettings()

# Переопределяем функцию get_settings в модуле config
import database.config
database.config.get_settings = override_get_settings

# Переопределяем функцию create_engine в sqlmodel для тестов
def override_sqlmodel_create_engine(url, **kwargs):
    """Тестовая версия create_engine без параметров, не поддерживаемых SQLite"""
    from sqlalchemy import create_engine
    # Убираем параметры, не поддерживаемые SQLite
    kwargs.pop('max_overflow', None)
    kwargs.pop('pool_size', None)
    # Убираем echo из kwargs, если он есть, чтобы избежать дублирования
    kwargs.pop('echo', None)
    return create_engine(
        url=url,
        echo=False,
        connect_args={"check_same_thread": False},
        **kwargs
    )

# Переопределяем функцию create_engine в sqlmodel
import sqlmodel
sqlmodel.create_engine = override_sqlmodel_create_engine

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session as SQLModelSession

# Тестовая база данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_session():
    """Переопределение сессии для тестов"""
    try:
        db = SQLModelSession(engine)
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def app():
    """Создание тестового приложения"""
    # Импортируем после установки переменных окружения
    from database.database import get_session
    from sqlmodel import SQLModel as Base
    from api import create_application
    
    # Создаем таблицы в тестовой базе
    Base.metadata.create_all(bind=engine)
    
    app = create_application()
    app.dependency_overrides[get_session] = override_get_session
    return app

@pytest.fixture(scope="session")
def client(app):
    """Создание тестового клиента"""
    return TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """Создание сессии базы данных для каждого теста"""
    session = SQLModelSession(engine)
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def hash_password():
    """Фикстура для хеширования паролей"""
    from auth.hash_password import HashPassword
    return HashPassword()

@pytest.fixture
def test_user_data():
    """Тестовые данные пользователя"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "name": "Test User"  # Исправлено: используем name вместо first_name и last_name
    }

@pytest.fixture
def test_user(db_session, hash_password, test_user_data):
    """Создание тестового пользователя"""
    from models.user import User
    
    hashed_password = hash_password.create_hash(test_user_data["password"])
    user = User(
        email=test_user_data["email"],
        hashed_password=hashed_password,  # Исправлено: используем hashed_password вместо password
        name=test_user_data["name"],  # Исправлено: используем name
        external_id="test_external_123",
        is_superuser=True  # Добавляем права суперпользователя для тестирования
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user):
    """Заголовки авторизации для тестового пользователя"""
    from auth.jwt_handler import create_access_token
    token = create_access_token(test_user.email)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_hall(db_session):
    """Создание тестового зала"""
    from models.hall import Hall
    
    hall = Hall(
        name="Тестовый зал",
        address="ул. Тестовая, 1",
        seats=100,  # Исправлено: используем seats вместо capacity
        concert_count=5  # Добавляем обязательное поле
    )
    db_session.add(hall)
    db_session.commit()
    db_session.refresh(hall)
    return hall

@pytest.fixture
def test_artist(db_session):
    """Создание тестового артиста"""
    from models.artist import Artist
    
    artist = Artist(
        name="Тестовый Артист",
        is_special=False
    )
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist

@pytest.fixture
def test_composition(db_session):
    """Создание тестового произведения"""
    from models.composition import Composition
    
    composition = Composition(
        name="Тестовое произведение",
        author_id=1
    )
    db_session.add(composition)
    db_session.commit()
    db_session.refresh(composition)
    return composition

@pytest.fixture
def test_concert(db_session, test_hall):
    """Создание тестового концерта"""
    from datetime import datetime, timedelta
    from models.concert import Concert
    
    concert = Concert(
        name="Тестовый концерт",
        datetime=datetime.now() + timedelta(days=1),
        hall_id=test_hall.id,
        genre="Классика",
        duration=timedelta(hours=2),
        external_id=12345  # Добавляем обязательное поле
    )
    db_session.add(concert)
    db_session.commit()
    db_session.refresh(concert)
    return concert

@pytest.fixture
def test_purchase(db_session, test_user, test_concert):
    """Создание тестовой покупки"""
    from datetime import datetime
    from models.purchase import Purchase
    
    purchase = Purchase(
        external_op_id=12345,  # Добавляем обязательное поле
        user_external_id=test_user.external_id,
        concert_id=test_concert.id,
        purchased_at=datetime.now(),
        price=1000
    )
    db_session.add(purchase)
    db_session.commit()
    db_session.refresh(purchase)
    return purchase 