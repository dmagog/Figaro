from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import init_db
from database.config import get_settings
from services.logging.logging import get_logger
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from routes.home import home_route
from routes.auth import auth_route
from routes.user import user_route
from routes.purchase import purchase_route
from routes.tickets import tickets_route

logger = get_logger(logger_name=__name__)
settings = get_settings()

def create_application() -> FastAPI:
    """
    Создание и конфигурация FastAPI приложения.
    
    Возвращает:
        FastAPI: Настроенный экземпляр приложения
    """
    # Создание приложения
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )

    # app.add_middleware(Analytics, api_key="39d40b20-6328-4a67-ae74-940f0cab5737")  # Добавление промежуточного слоя
    
    # Настройка CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Монтируем папку static
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Регистрация маршрутов
    app.include_router(home_route, tags=['Home'])
    app.include_router(auth_route, tags=['Auth'])
    app.include_router(user_route, tags=['User'])
    app.include_router(purchase_route, tags=['Purchase'])
    app.include_router(tickets_route, tags=['Tickets'])
    # app.include_router(admin_route, tags=['Admin'])
    


    return app

app = create_application()

@app.on_event("startup") 
def on_startup():
    try:
        logger.info("Инициализация базы данных...")
        init_db(demostart = False)
        logger.info("Запуск приложения успешно завершен")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {str(e)}")
        raise   
    

if __name__ == '__main__':
    uvicorn.run('api:app', host='0.0.0.0', port=8080, reload=True, log_level="info")
