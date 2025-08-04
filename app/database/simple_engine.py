from sqlmodel import create_engine
from .config import get_settings

# Простой engine без импорта моделей
settings = get_settings()
simple_engine = create_engine(url=settings.DATABASE_URL_psycopg, echo=False) 