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
from app.services.crud.purchase import get_user_unique_concerts_with_details
from app.routes.user.temp_routes import calculate_transition_time, calculate_route_statistics

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

@api_router.get("/api/user/route-data/{user_external_id}")
async def get_user_route_data_api(user_external_id: str, session=Depends(get_session)):
    """API endpoint для получения данных маршрута пользователя"""
    try:
        # Получаем концерты пользователя
        concerts_data = get_user_unique_concerts_with_details(session, user_external_id)
        
        if not concerts_data:
            return {"error": "У вас нет концертов в маршруте"}
        
        # Сортируем концерты по времени
        from datetime import datetime
        sorted_concerts = sorted(concerts_data, key=lambda x: x['concert'].get('datetime', datetime.min))
        
        # Создаем структуру для статистики
        concerts_by_day_with_transitions = {}
        current_day = None
        day_concerts = []
        
        for i, concert_data in enumerate(sorted_concerts):
            concert = concert_data['concert']
            if concert.get('datetime'):
                day = concert['datetime'].date()
                if current_day != day:
                    if current_day and day_concerts:
                        concerts_by_day_with_transitions[current_day] = day_concerts
                    current_day = day
                    day_concerts = []
                
                # Добавляем информацию о переходе
                concert_with_transition = concert_data.copy()
                if i < len(sorted_concerts) - 1:
                    next_concert_data = sorted_concerts[i + 1]
                    transition_info = calculate_transition_time(session, concert_data, next_concert_data)
                    concert_with_transition['transition_info'] = transition_info
                else:
                    concert_with_transition['transition_info'] = None
                
                day_concerts.append(concert_with_transition)
        
        # Добавляем последний день
        if current_day and day_concerts:
            concerts_by_day_with_transitions[current_day] = day_concerts
        
        # Получаем статистику
        route_stats = calculate_route_statistics(session, sorted_concerts, concerts_by_day_with_transitions)
        
        return {
            "sorted_concerts": sorted_concerts,
            "route_summary": route_stats,
            "concerts_by_day": concerts_by_day_with_transitions
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении данных маршрута: {e}")
        return {"error": f"Ошибка при получении данных: {str(e)}"}

@api_router.post("/api/user/format-route")
async def format_route_concerts_list_api(
    concerts_data: dict,
    detailed: bool = False,
    day_number: int = None
):
    """API endpoint для форматирования списка концертов"""
    try:
        sorted_concerts = concerts_data.get("sorted_concerts", [])
        if not sorted_concerts:
            return "Маршрут не найден или пуст"
        
        # Группируем концерты по дням
        concerts_by_day = {}
        for i, concert_data in enumerate(sorted_concerts):
            concert = concert_data['concert']
            if concert.get('datetime'):
                day = concert['datetime'].date()
                if day not in concerts_by_day:
                    concerts_by_day[day] = []
                concerts_by_day[day].append({
                    'index': i + 1,
                    'time': concert['datetime'].strftime("%H:%M"),
                    'name': concert.get('name', 'Название не указано'),
                    'hall': concert.get('hall', {}).get('name', 'Зал не указан'),
                    'duration': str(concert.get('duration', 'Длительность не указана')),
                    'genre': concert.get('genre', 'Жанр не указан'),
                    'concert_data': concert_data
                })
        
        # Сортируем дни
        sorted_days = sorted(concerts_by_day.keys())
        
        if day_number:
            # Показываем только конкретный день
            try:
                day_index = int(day_number) - 1
                if 0 <= day_index < len(sorted_days):
                    target_day = sorted_days[day_index]
                    day_concerts = concerts_by_day[target_day]
                    
                    # Форматируем дату
                    day_str = str(target_day.day)
                    month_names = {
                        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                        5: "мая", 6: "июня", 7: "июля", 8: "августа",
                        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                    }
                    month_str = month_names.get(target_day.month, "месяца")
                    
                    concerts_text = f"🎈 *День {day_index + 1}* ({day_str} {month_str})\n\n"
                    
                    for concert in day_concerts:
                        if detailed:
                            concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                            concerts_text += f"   🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                            
                            if concert['concert_data'].get('transition_info'):
                                transition = concert['concert_data']['transition_info']
                                if transition.get('status') == 'success':
                                    concerts_text += f"   🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                                elif transition.get('status') == 'same_hall':
                                    concerts_text += f"   📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                            
                            concerts_text += "\n"
                        else:
                            concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
                    
                    return concerts_text
                else:
                    return f"День {day_number} не найден в маршруте"
            except ValueError:
                return f"Неверный номер дня: {day_number}"
        
        # Показываем все дни
        concerts_text = ""
        for day_index, target_day in enumerate(sorted_days, 1):
            day_concerts = concerts_by_day[target_day]
            
            # Форматируем дату
            day_str = str(target_day.day)
            month_names = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            month_str = month_names.get(target_day.month, "месяца")
            
            concerts_text += f"🎈 *День {day_index}* ({day_str} {month_str})\n\n"
            
            for concert in day_concerts:
                if detailed:
                    concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                    concerts_text += f"   🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                    
                    if concert['concert_data'].get('transition_info'):
                        transition = concert['concert_data']['transition_info']
                        if transition.get('status') == 'success':
                            concerts_text += f"   🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                        elif transition.get('status') == 'same_hall':
                            concerts_text += f"   📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                    
                    concerts_text += "\n"
                else:
                    concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
            
            concerts_text += "\n"
        
        return concerts_text.strip()
        
    except Exception as e:
        logger.error(f"Ошибка при форматировании маршрута: {e}")
        return f"Ошибка при форматировании: {str(e)}"

@api_router.post("/api/user/format-summary")
async def format_route_summary_api(request_data: dict):
    """API endpoint для форматирования статистики маршрута"""
    try:
        # Извлекаем concerts_data из запроса
        concerts_data = request_data.get("concerts_data", {})
        if not concerts_data:
            return "Данные концертов не найдены"
        
        route_summary = concerts_data.get("route_summary", {})
        if not route_summary:
            return "Статистика маршрута недоступна"
        
        # Проверяем, что route_summary не пустой
        if not isinstance(route_summary, dict) or len(route_summary) == 0:
            return "Статистика маршрута недоступна"
        
        summary_text = "📊 *Итоговая статистика маршрута:*\n\n"
        
        # Основные показатели
        summary_text += f"🎵 *Концертов:* {route_summary.get('total_concerts', 0)}\n"
        summary_text += f"📅 *Дней:* {route_summary.get('total_days', 0)}\n"
        summary_text += f"🏛️ *Залов:* {route_summary.get('total_halls', 0)}\n"
        summary_text += f"🎨 *Жанров:* {route_summary.get('total_genres', 0)}\n"
        
        # Время
        concert_time = route_summary.get('total_concert_time_minutes', 0)
        if concert_time:
            summary_text += f"⏱️ *Время концертов:* {concert_time} мин\n"
        
        trans_time = route_summary.get('total_walk_time_minutes', 0)
        if trans_time:
            summary_text += f"🚶 *Время переходов:* {trans_time} мин\n"
        
        # Расстояние
        distance = route_summary.get('total_distance_km', 0)
        if distance:
            summary_text += f"📍 *Пройдено:* {distance} км\n"
        
        # Контент
        compositions = route_summary.get('unique_compositions', 0)
        if compositions:
            summary_text += f"🎼 *Произведений:* {compositions}\n"
        
        authors = route_summary.get('unique_authors', 0)
        if authors:
            summary_text += f"✍️ *Авторов:* {authors}\n"
        
        artists = route_summary.get('unique_artists', 0)
        if artists:
            summary_text += f"🎭 *Артистов:* {artists}\n"
        
        summary_text += "\n🎉 *Спасибо, что выбрали наш фестиваль! До встречи на концертах!*"
        
        return summary_text
        
    except Exception as e:
        logger.error(f"Ошибка при форматировании статистики: {e}")
        return f"Ошибка при форматировании статистики: {str(e)}"


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
