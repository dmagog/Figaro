from fastapi import APIRouter, HTTPException, status, Depends, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database.database import get_session
from models.user import *
from services.crud import user as UserService
from services.crud import purchase as PurchaseService
from typing import List, Dict
from services.logging.logging import get_logger
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from auth.authenticate import authenticate_cookie
from models import User
from database.config import get_settings
from fastapi.responses import JSONResponse

logger = get_logger(logger_name=__name__)

user_route = APIRouter()
hash_password = HashPassword()
settings = get_settings()

# Инициализируем шаблонизатор Jinja2
templates = Jinja2Templates(directory="templates")

user_route = APIRouter(tags=['User'])

@user_route.post('/signup')
async def signup(user: User, session=Depends(get_session)) -> dict:
    try:
        user_exist = UserService.get_user_by_email(user.email, session)
        
        if user_exist:
            raise HTTPException( 
            status_code=status.HTTP_409_CONFLICT, 
            detail="User with email provided exists already.")
        
        hashed_password = hash_password.create_hash(user.password)
        user.password = hashed_password 
        UserService.create_user(user, 
                            Bill(balance=10, freeLimit_perDay=3, freeLimit_today=3), 
                            session)
        
        return {"message": "User created successfully"}

    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )



# @user_route.post('/signin')
# async def signin(data: User, session=Depends(get_session)) -> dict:
#     user = UserService.get_user_by_email(data.email, session)
#     if user is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
#     if user.password != data.password:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong credentials passed")
    
#     return {"message": "User signed in successfully"}


@user_route.post('/signin')
async def signin(form_data: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)) -> Dict[str, str]:
    """
    """
    user_exist = UserService.get_user_by_email(form_data.username, session)
    
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    if hash_password.verify_hash(form_data.password, user_exist.password):
        access_token = create_access_token(user_exist.email)
        return {"access_token": access_token, "token_type": "Bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )



@user_route.get("/email/{email}", response_model=User) 
async def get_user_by_email(email: str, session=Depends(get_session)) -> User:
    user = UserService.get_user_by_email(email, session)
    if user:
        return user 
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Users with supplied EMAIL does not exist")


@user_route.get("/id/{id}", response_model=User) 
async def get_user_by_id(id: int, session=Depends(get_session)) -> User:
    user = UserService.get_user_by_id(id, session)
    if user:
        return user 
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Users with supplied ID does not exist")



@user_route.get(
    "/get_all_users",
    response_model=List[User],
    summary="Получение списка пользователей",
    response_description="Список всех пользователей"
)
async def get_all_users(session=Depends(get_session)) -> List[User]:
    """
    Получение списка всех пользователей.

    Аргументы:
        session: Сессия базы данных

    Возвращает:
        List[User]: Список пользователей

    Исключения:
        HTTPException: Если возникла ошибка при получении списка пользователей
    """
    try:
        users = UserService.get_all_users(session)
        logger.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving users"
        )
    


@user_route.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    session=Depends(get_session)
):
    """
    Страница личного кабинета пользователя
    
    Args:
        request: Объект HTTP-запроса
        session: Сессия базы данных
        
    Returns:
        HTML-страница личного кабинета
    """
    # Проверяем аутентификацию
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        # Получаем email из токена
        user_email = await authenticate_cookie(token)
        if not user_email:
            return RedirectResponse(url="/login", status_code=302)
        
        # Получаем пользователя из базы
        current_user = UserService.get_user_by_email(user_email, session)
        if not current_user:
            return RedirectResponse(url="/login", status_code=302)
        
        # Отладочная информация
        logger.info(f"User found: {current_user.email}, external_id: {current_user.external_id}")
        
        # Получаем данные о покупках пользователя
        # Используем external_id пользователя для поиска покупок
        user_external_id = current_user.external_id
        
        if not user_external_id:
            # Если у пользователя нет external_id, показываем пустую страницу
            logger.warning(f"User {current_user.email} has no external_id")
            context = {
                "request": request,
                "user": current_user,
                "purchases": [],
                "purchase_summary": {
                    "total_purchases": 0,
                    "total_spent": 0,
                    "total_concerts": 0,
                    "unique_halls": 0,
                    "genres": []
                }
            }
            return templates.TemplateResponse("profile.html", context)
        
        # Отладочная информация о поиске покупок
        logger.info(f"Searching purchases for external_id: {user_external_id}")
        
        # Получаем покупки с деталями
        purchases = PurchaseService.get_user_purchases_with_details(session, user_external_id)
        
        logger.info(f"Found {len(purchases)} purchases for user {user_external_id}")
        
        # Получаем сводную информацию
        purchase_summary = {
            "total_purchases": len(purchases),
            "total_spent": sum(p.get('price', 0) or 0 for p in purchases),
            "total_concerts": len(set(p['concert']['id'] for p in purchases)),
            "unique_halls": len(set(p['concert']['hall']['id'] for p in purchases if p['concert']['hall'])),
            "genres": list(set(p['concert']['genre'] for p in purchases if p['concert']['genre']))
        }
        
        logger.info(f"Purchase summary: {purchase_summary}")
        
        # Группируем покупки по уникальным концертам
        unique_concerts = {}
        for purchase in purchases:
            concert_id = purchase['concert']['id']
            if concert_id not in unique_concerts:
                unique_concerts[concert_id] = {
                    'concert': purchase['concert'],
                    'tickets_count': 1,
                    'total_spent': purchase.get('price', 0) or 0
                }
            else:
                unique_concerts[concert_id]['tickets_count'] += 1
                unique_concerts[concert_id]['total_spent'] += purchase.get('price', 0) or 0
        
        logger.info(f"Found {len(unique_concerts)} unique concerts")
        
        # Упрощаем преобразование данных для шаблона
        concerts_for_template = []
        for concert_id, concert_data in unique_concerts.items():
            try:
                # Создаем копию данных концерта
                concert_copy = concert_data.copy()
                
                # Проверяем тип данных перед преобразованием
                from datetime import datetime
                
                # Обрабатываем concert datetime
                if isinstance(concert_data['concert']['datetime'], str):
                    concert_copy['concert']['datetime'] = datetime.fromisoformat(concert_data['concert']['datetime'])
                else:
                    concert_copy['concert']['datetime'] = concert_data['concert']['datetime']
                
                # Преобразуем duration обратно в timedelta
                from datetime import timedelta
                duration_str = concert_data['concert']['duration']
                if isinstance(duration_str, (int, float)):
                    # Если duration в секундах
                    concert_copy['concert']['duration'] = timedelta(seconds=duration_str)
                elif isinstance(duration_str, str) and ':' in duration_str:
                    # Если duration в формате HH:MM:SS
                    parts = duration_str.split(':')
                    if len(parts) >= 2:
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        concert_copy['concert']['duration'] = timedelta(hours=hours, minutes=minutes)
                else:
                    # Оставляем как есть
                    concert_copy['concert']['duration'] = duration_str
                
                concerts_for_template.append(concert_copy)
                logger.info(f"Processed unique concert: {concert_copy['concert']['name']} ({concert_copy['tickets_count']} tickets)")
                
            except Exception as e:
                logger.error(f"Error processing concert: {e}")
                # Добавляем концерт без обработки datetime
                concerts_for_template.append(concert_data)
                continue
        
        # Сортируем концерты по дате (по возрастанию)
        concerts_for_template.sort(key=lambda x: x['concert']['datetime'] if x['concert']['datetime'] else datetime.min)
        
        # Группируем по дате (день фестиваля)
        from collections import defaultdict
        day_to_index = {}
        unique_days = []
        logger.info(f"Processing {len(concerts_for_template)} concerts for day indexing")
        
        for i, concert in enumerate(concerts_for_template):
            dt = concert['concert']['datetime']
            if dt:
                day = dt.date()
                if day not in day_to_index:
                    day_to_index[day] = len(day_to_index) + 1
                concert['concert_day_index'] = day_to_index[day]
                logger.info(f"Concert {i}: date={day}, day_index={day_to_index[day]}")
            else:
                concert['concert_day_index'] = 0
                logger.warning(f"Concert {i}: no datetime, day_index=0")
        
        logger.info(f"Day to index mapping: {day_to_index}")
        
        # Добавляем номера концертов
        for i, concert_data in enumerate(concerts_for_template, 1):
            concert_data['concert_number'] = i
        
        logger.info(f"Processed {len(concerts_for_template)} unique concerts for template")
        
        # Получаем данные для маршрутного листа
        route_sheet_data = get_user_route_sheet(session, user_external_id, concerts_for_template)
        
        # Отладочная информация для маршрутного листа
        logger.info(f"Route sheet data: {route_sheet_data}")
        logger.info(f"Concerts by day: {route_sheet_data.get('concerts_by_day', {})}")
        
        context = {
            "request": request,
            "user": current_user,
            "concerts": concerts_for_template,  # Изменили название с purchases на concerts
            "purchase_summary": purchase_summary,
            "route_sheet": route_sheet_data
        }
        
        return templates.TemplateResponse("profile.html", context)
        
    except Exception as e:
        logger.error(f"Error loading profile page: {str(e)}")
        # В случае ошибки перенаправляем на главную
        return RedirectResponse(url="/", status_code=302)
    


@user_route.post("/profile/set_external_id")
async def set_profile_external_id(request: Request, session=Depends(get_session)):
    token = request.cookies.get(settings.COOKIE_NAME)
    user_email = None
    if token:
        user_email = await authenticate_cookie(token)
    if not user_email:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user = UserService.get_user_by_email(user_email, session)
    if not user or not getattr(user, 'is_superuser', False):
        return JSONResponse({"success": False, "error": "Доступ запрещён"}, status_code=403)
    data = await request.json()
    new_external_id = data.get('external_id')
    if not new_external_id:
        return JSONResponse({"success": False, "error": "Некорректные данные"}, status_code=400)
    user.external_id = new_external_id
    session.add(user)
    session.commit()
    session.refresh(user)
    return JSONResponse({"success": True, "external_id": user.external_id})


@user_route.get("/debug/user/{email}/external_id")
async def debug_user_external_id(
    email: str,
    session=Depends(get_session)
):
    """
    Временный endpoint для отладки external_id пользователя
    """
    try:
        user = UserService.get_user_by_email(email, session)
        if not user:
            return {"error": "User not found"}
        
        return {
            "email": user.email,
            "external_id": user.external_id,
            "id": user.id
        }
    except Exception as e:
        return {"error": str(e)}


@user_route.post("/debug/user/{email}/set_external_id/{external_id}")
async def set_user_external_id(
    email: str,
    external_id: str,
    session=Depends(get_session)
):
    """
    Временный endpoint для установки external_id пользователя
    """
    try:
        user = UserService.get_user_by_email(email, session)
        if not user:
            return {"error": "User not found"}
        
        user.external_id = external_id
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return {
            "success": True,
            "email": user.email,
            "external_id": user.external_id
        }
    except Exception as e:
        return {"error": str(e)}


@user_route.get("/debug/purchases/{external_id}")
async def debug_user_purchases(
    external_id: str,
    session=Depends(get_session)
):
    """
    Временный endpoint для проверки покупок пользователя
    """
    try:
        purchases = PurchaseService.get_user_purchases_with_details(session, external_id)
        return {
            "external_id": external_id,
            "purchases_count": len(purchases),
            "purchases": purchases[:3]  # Показываем только первые 3 покупки
        }
    except Exception as e:
        return {"error": str(e)}
    


    

def get_user_route_sheet(session, user_external_id: str, concerts_data: list) -> dict:
    """
    Получает данные для маршрутного листа пользователя
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с данными маршрутного листа
    """
    try:
        from models import Route, CustomerRouteMatch
        from sqlalchemy import select
        
        # Получаем ID концертов пользователя
        user_concert_ids = [c['concert']['id'] for c in concerts_data]
        user_concert_ids_str = ",".join(map(str, sorted(user_concert_ids)))
        
        # Ищем существующее соответствие маршрута
        existing_match = session.exec(
            select(CustomerRouteMatch)
            .where(CustomerRouteMatch.user_external_id == user_external_id)
        ).first()
        
        if existing_match:
            # Если есть сохраненное соответствие, используем его
            try:
                match_data = {
                    "found": getattr(existing_match, 'found', False),
                    "match_type": getattr(existing_match, 'match_type', 'none'),
                    "reason": getattr(existing_match, 'reason', 'Неизвестная причина'),
                    "match_percentage": getattr(existing_match, 'match_percentage', 0.0),
                    "total_routes_checked": getattr(existing_match, 'total_routes_checked', 0),
                    "customer_concerts": existing_match.customer_concerts.split(',') if existing_match.customer_concerts else [],
                    "best_route": None
                }
            except Exception as e:
                logger.error(f"Ошибка при обработке существующего соответствия: {e}")
                match_data = {
                    "found": False,
                    "match_type": "error",
                    "reason": "Ошибка при обработке данных",
                    "match_percentage": 0.0,
                    "total_routes_checked": 0,
                    "customer_concerts": [],
                    "best_route": None
                }
            
            if getattr(existing_match, 'found', False) and getattr(existing_match, 'best_route_id', None):
                best_route = session.exec(
                    select(Route).where(Route.id == getattr(existing_match, 'best_route_id', None))
                ).first()
                
                if best_route:
                    match_data["best_route"] = {
                        "id": best_route.id,
                        "composition": best_route.Sostav,
                        "days": best_route.Days,
                        "concerts": best_route.Concerts,
                        "halls": best_route.Halls,
                        "genre": best_route.Genre,
                        "show_time": best_route.ShowTime,
                        "trans_time": best_route.TransTime,
                        "wait_time": best_route.WaitTime,
                        "costs": best_route.Costs,
                        "comfort_score": best_route.ComfortScore,
                        "comfort_level": best_route.ComfortLevel,
                        "intellect_score": best_route.IntellectScore,
                        "intellect_category": best_route.IntellectCategory
                    }
        else:
            # Ищем соответствие среди всех маршрутов
            all_routes = session.exec(select(Route)).all()
            
            exact_matches = []
            partial_matches = []
            
            for route in all_routes:
                try:
                    # Парсим состав маршрута
                    route_concert_ids = sorted([int(x.strip()) for x in route.Sostav.split(',') if x.strip()])
                    
                    # Проверяем точное совпадение
                    if route_concert_ids == sorted(user_concert_ids):
                        exact_matches.append({
                            "id": route.id,
                            "composition": route.Sostav,
                            "days": route.Days,
                            "concerts": route.Concerts,
                            "halls": route.Halls,
                            "genre": route.Genre,
                            "show_time": route.ShowTime,
                            "trans_time": route.TransTime,
                            "wait_time": route.WaitTime,
                            "costs": route.Costs,
                            "comfort_score": route.ComfortScore,
                            "comfort_level": route.ComfortLevel,
                            "intellect_score": route.IntellectScore,
                            "intellect_category": route.IntellectCategory,
                            "match_type": "exact",
                            "match_percentage": 100.0
                        })
                    
                    # Проверяем частичное совпадение
                    elif set(user_concert_ids).issubset(set(route_concert_ids)):
                        match_percentage = (len(user_concert_ids) / len(route_concert_ids)) * 100
                        partial_matches.append({
                            "id": route.id,
                            "composition": route.Sostav,
                            "days": route.Days,
                            "concerts": route.Concerts,
                            "halls": route.Halls,
                            "genre": route.Genre,
                            "show_time": route.ShowTime,
                            "trans_time": route.TransTime,
                            "wait_time": route.WaitTime,
                            "costs": route.Costs,
                            "comfort_score": route.ComfortScore,
                            "comfort_level": route.ComfortLevel,
                            "intellect_score": route.IntellectScore,
                            "intellect_category": route.IntellectCategory,
                            "match_type": "partial",
                            "match_percentage": match_percentage,
                            "missing_concerts": list(set(route_concert_ids) - set(user_concert_ids))
                        })
                        
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Ошибка при парсинге маршрута {route.id}: {e}")
                    continue
            
            # Сортируем частичные совпадения по проценту совпадения
            partial_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
            
            # Формируем результат
            if exact_matches:
                match_data = {
                    "found": True,
                    "match_type": "exact",
                    "reason": "Найдено точное совпадение с маршрутом",
                    "match_percentage": 100.0,
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": exact_matches[0]
                }
            elif partial_matches:
                match_data = {
                    "found": True,
                    "match_type": "partial",
                    "reason": f"Найдено частичное совпадение с маршрутом ({partial_matches[0]['match_percentage']:.1f}%)",
                    "match_percentage": partial_matches[0]["match_percentage"],
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": partial_matches[0]
                }
            else:
                match_data = {
                    "found": False,
                    "match_type": "none",
                    "reason": "Не найдено подходящих маршрутов",
                    "match_percentage": 0.0,
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": None
                }
        
        # Отладочная информация
        logger.info(f"Processing route sheet for {len(concerts_data)} concerts")
        logger.info(f"Concert day indices: {[c.get('concert_day_index', 0) for c in concerts_data]}")
        
        # Проверяем структуру данных концертов
        for i, concert in enumerate(concerts_data):
            logger.info(f"Concert {i}: day_index={concert.get('concert_day_index', 0)}, "
                       f"hall={concert['concert'].get('hall', 'No hall')}, "
                       f"genre={concert['concert'].get('genre', 'No genre')}")
        
        # Группируем концерты по дням
        concerts_by_day = group_concerts_by_day(concerts_data)
        logger.info(f"Concerts grouped by day: {concerts_by_day}")
        
        # Безопасный подсчет статистики
        total_days = len(set(c.get('concert_day_index', 0) for c in concerts_data if c.get('concert_day_index', 0) > 0))
        
        hall_ids = set()
        for c in concerts_data:
            hall = c['concert'].get('hall')
            if hall and isinstance(hall, dict) and 'id' in hall:
                hall_ids.add(hall['id'])
        total_halls = len(hall_ids)
        
        genres = set()
        for c in concerts_data:
            genre = c['concert'].get('genre')
            if genre:
                genres.add(genre)
        total_genres = len(genres)
        
        return {
            "summary": {
                "total_concerts": len(concerts_data),
                "total_days": total_days,
                "total_halls": total_halls,
                "total_genres": total_genres,
                "total_spent": sum(c['total_spent'] for c in concerts_data)
            },
            "match": match_data,
            "concerts_by_day": concerts_by_day
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении маршрутного листа: {e}")
        return {
            "summary": {
                "total_concerts": len(concerts_data),
                "total_days": 0,
                "total_halls": 0,
                "total_genres": 0,
                "total_spent": sum(c['total_spent'] for c in concerts_data)
            },
            "match": {
                "found": False,
                "match_type": "error",
                "reason": "Ошибка при анализе маршрутов",
                "match_percentage": 0.0,
                "total_routes_checked": 0,
                "customer_concerts": [],
                "best_route": None
            },
            "concerts_by_day": {}
        }


def group_concerts_by_day(concerts_data: list) -> dict:
    """
    Группирует концерты по дням фестиваля
    
    Args:
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с концертами, сгруппированными по дням
    """
    from datetime import datetime
    
    concerts_by_day = {}
    
    logger.info(f"Starting to group {len(concerts_data)} concerts by day")
    
    for i, concert in enumerate(concerts_data):
        day_index = concert.get('concert_day_index', 0)
        logger.info(f"Concert {i}: day_index={day_index}")
        
        if day_index > 0:
            if day_index not in concerts_by_day:
                concerts_by_day[day_index] = []
            concerts_by_day[day_index].append(concert)
            logger.info(f"Added concert to day {day_index}")
        else:
            logger.warning(f"Concert {i} has day_index=0, skipping")
    
    # Сортируем концерты в каждом дне по времени
    for day_concerts in concerts_by_day.values():
        try:
            day_concerts.sort(key=lambda x: x['concert'].get('datetime') if x['concert'].get('datetime') else datetime.min)
        except Exception as e:
            logger.warning(f"Error sorting concerts by time: {e}")
            # Если не удалось отсортировать, оставляем как есть
            pass
    
    logger.info(f"Final grouped concerts by day: {concerts_by_day}")
    return concerts_by_day
    


    
