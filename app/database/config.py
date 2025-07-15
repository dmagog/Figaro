from pydantic import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    DB_HOST: Optional[str] = None    # Хост базы данных
    DB_PORT: Optional[int] = None    # Порт базы данных
    DB_USER: Optional[str] = None    # Имя пользователя БД
    DB_PASS: Optional[str] = None    # Пароль пользователя БД
    DB_NAME: Optional[str] = None    # Название базы данных
    COOKIE_NAME: Optional[str] = None # Название cookie
    SECRET_KEY: Optional[str] = None  # Секретный ключ
    
    # RABBITMQ_HOST: Optional[str] = None 
    # RABBITMQ_PORT: Optional[int] = None 
    RABBITMQ_USER: Optional[str] = None 
    RABBITMQ_PASS: Optional[str] = None 

    # Настройки приложения
    APP_NAME: Optional[str] = 'My app'        # Название приложения
    APP_DESCRIPTION: Optional[str] = 'Very best app' # Описание приложения
    DEBUG: Optional[bool] = None          # Режим отладки
    API_VERSION: Optional[str] = '0.1'     # Версия API
    

    @property
    def DATABASE_URL_asyncpg(self):
        return f'postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
    
    @property
    def DATABASE_URL_psycopg(self):
        return f'postgresql+psycopg2://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}'
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


    def validate(self) -> None:
        """Проверка критических параметров конфигурации"""
        if not all([self.DB_HOST, self.DB_USER, self.DB_PASS, self.DB_NAME]):
            raise ValueError("Отсутствуют необходимые параметры конфигурации базы данных")


@lru_cache()
def get_settings() -> Settings:
    """Получение настроек приложения с кэшированием"""
    settings = Settings()
    settings.validate()
    return settings
