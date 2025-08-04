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

from fastapi import APIRouter, Depends, HTTPException, status, Request
from worker.tasks import send_telegram_message
from app.services.crud import user as UserService
from app.database.database import get_session
from app.auth.authenticate import authenticate_cookie
from fastapi import UploadFile, File, Form
import shutil
from tempfile import NamedTemporaryFile
from sqlalchemy import select
from models.user import User


logger = get_logger(logger_name=__name__)
settings = get_settings()

api_router = APIRouter()

@api_router.post("/telegram/send-test")
async def send_test_telegram_message(request: Request, session=Depends(get_session)):
    token = request.cookies.get("access_token") or request.cookies.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user_email = await authenticate_cookie(token)
    if not user_email:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user = UserService.get_user_by_email(user_email, session)
    if not user or not user.telegram_id:
        raise HTTPException(status_code=404, detail="Telegram не привязан")
    # Ставим задачу в очередь
    send_telegram_message.delay(user.telegram_id, "Тестовое сообщение из FastAPI через Celery!", None, None, "Markdown")
    return {"success": True, "message": "Задача на отправку сообщения поставлена в очередь."}

# Импортируем роутер для бота API
from app.routes.bot_api import bot_api_router

@api_router.post("/admin/telegram/broadcast")
async def broadcast_telegram_message(
    request: Request,
    session=Depends(get_session),
    text: str = Form(None),
    file: UploadFile = File(None),
    file_type: str = Form(None)
):
    token = request.cookies.get("access_token") or request.cookies.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user_email = await authenticate_cookie(token)
    if not user_email:
        raise HTTPException(status_code=401, detail="Не авторизован")
    user = UserService.get_user_by_email(user_email, session)
    if not user or not user.is_superuser:
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    # Получаем всех пользователей с telegram_id
    users = session.exec(select(User).where(User.telegram_id.is_not(None))).all()
    if not users:
        return {"success": False, "message": "Нет пользователей с привязанным Telegram."}
    file_path = None
    temp_file = None
    if file:
        suffix = ".jpg" if file_type == "photo" else ".pdf" if file_type == "document" else ""
        temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
        with temp_file as f:
            shutil.copyfileobj(file.file, f)
        file_path = temp_file.name
    count = 0
    for u in users:
        send_telegram_message.delay(u.telegram_id, text, file_path, file_type, "Markdown")
        count += 1
    # Удаляем временный файл после рассылки (если был)
    if temp_file:
        temp_file.close()
    return {"success": True, "message": f"Поставлено задач: {count}", "users": count}




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
    app.include_router(api_router, tags=['API'])
    app.include_router(bot_api_router, tags=['Bot API'])
    


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
