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
        
        # Добавляем информацию о переходах между концертами
        concerts_by_day_with_transitions = {}
        for day_index, day_concerts in concerts_by_day.items():
            concerts_with_transitions = []
            
            for i, concert in enumerate(day_concerts):
                concert_with_transition = concert.copy()
                
                # Добавляем информацию о переходе к следующему концерту
                if i < len(day_concerts) - 1:
                    next_concert = day_concerts[i + 1]
                    transition_info = calculate_transition_time(session, concert, next_concert)
                    concert_with_transition['transition_info'] = transition_info
                else:
                    concert_with_transition['transition_info'] = None
                
                concerts_with_transitions.append(concert_with_transition)
            
            concerts_by_day_with_transitions[day_index] = concerts_with_transitions
        
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
            "concerts_by_day": concerts_by_day_with_transitions
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


def calculate_transition_time(session, current_concert: dict, next_concert: dict) -> dict:
    """
    Рассчитывает время перехода между двумя концертами
    
    Args:
        session: Сессия базы данных
        current_concert: Текущий концерт
        next_concert: Следующий концерт
        
    Returns:
        Словарь с информацией о переходе
    """
    try:
        from datetime import datetime, timedelta
        
        # Получаем ID залов
        current_hall_id = current_concert['concert'].get('hall', {}).get('id')
        next_hall_id = next_concert['concert'].get('hall', {}).get('id')
        
        logger.info(f"Calculating transition: hall {current_hall_id} -> {next_hall_id}")
        
        if not current_hall_id or not next_hall_id:
            logger.warning(f"No hall info: current_hall_id={current_hall_id}, next_hall_id={next_hall_id}")
            return {
                'time_between': 0,
                'walk_time': 0,
                'status': 'no_hall_info'
            }
        
        # Если концерты в одном зале, время перехода = 0
        if current_hall_id == next_hall_id:
            logger.info(f"Same hall ({current_hall_id}), no transition needed")
            return {
                'time_between': 0,
                'walk_time': 0,
                'status': 'same_hall'
            }
        
        # Получаем время начала и окончания концертов
        current_start = current_concert['concert'].get('datetime')
        current_duration = current_concert['concert'].get('duration')
        next_start = next_concert['concert'].get('datetime')
        
        logger.info(f"Times: current_start={current_start}, next_start={next_start}, current_duration={current_duration}")
        
        if not current_start or not next_start:
            logger.warning(f"No time info: current_start={current_start}, next_start={next_start}")
            return {
                'time_between': 0,
                'walk_time': 0,
                'status': 'no_time_info'
            }
        
        # Рассчитываем время окончания текущего концерта
        if current_duration and hasattr(current_duration, 'seconds'):
            current_end = current_start + timedelta(seconds=current_duration.seconds)
        elif current_duration and isinstance(current_duration, timedelta):
            current_end = current_start + current_duration
        else:
            # Если нет информации о длительности, предполагаем 90 минут
            current_end = current_start + timedelta(minutes=90)
        
        logger.info(f"Current end time: {current_end}")
        
        # Рассчитываем время между концертами
        time_between = (next_start - current_end).total_seconds() / 60  # в минутах
        
        logger.info(f"Time between concerts: {time_between} minutes")
        
        # Получаем время перехода между залами через SQLModel
        from models import HallTransition
        from sqlalchemy import select

        # Ищем переход в прямом направлении
        transition = session.exec(
            select(HallTransition)
            .where(HallTransition.from_hall_id == current_hall_id)
            .where(HallTransition.to_hall_id == next_hall_id)
        ).first()

        # Если не найден прямой переход, ищем обратный
        if not transition:
            transition = session.exec(
                select(HallTransition)
                .where(HallTransition.from_hall_id == next_hall_id)
                .where(HallTransition.to_hall_id == current_hall_id)
            ).first()

        if transition:
            try:
                # Если это Row-объект, извлекаем данные через _asdict()
                if hasattr(transition, '_asdict'):
                    transition_dict = transition._asdict()
                    
                    # Row содержит объект модели под ключом 'HallTransition'
                    if 'HallTransition' in transition_dict:
                        hall_transition_obj = transition_dict['HallTransition']
                        walk_time = hall_transition_obj.transition_time
                    else:
                        walk_time = transition_dict.get('transition_time')
                else:
                    walk_time = transition.transition_time
                
                if walk_time is not None:
                    logger.info(f"Found transition: {current_hall_id} <-> {next_hall_id} = {walk_time} minutes")
            except Exception as e:
                logger.error(f"Error accessing transition_time: {e}")
                walk_time = None
        else:
            walk_time = None
            logger.error(f"No transition found for {current_hall_id} <-> {next_hall_id}")
        
        # Определяем статус перехода
        if walk_time is None:
            status = 'no_transition_data'  # Нет данных о переходе
        elif time_between < walk_time:
            status = 'warning'  # Недостаточно времени
        elif time_between < walk_time + 10:
            status = 'tight'    # Впритык
        else:
            status = 'success'  # Достаточно времени
        
        logger.info(f"Transition status: {status} (time_between={time_between}, walk_time={walk_time})")
        
        return {
            'time_between': int(time_between),
            'walk_time': walk_time,
            'status': status,
            'current_end': current_end.strftime('%H:%M'),
            'next_start': next_start.strftime('%H:%M')
        }
        
    except Exception as e:
        logger.error(f"Error calculating transition time: {e}")
        return {
            'time_between': 0,
            'walk_time': 0,
            'status': 'error'
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
    


    

@user_route.get("/debug/transitions")
async def debug_transitions(session=Depends(get_session)):
    """Отладочный endpoint для проверки данных о переходах между залами"""
    try:
        from models import Hall, HallTransition
        from sqlmodel import select
        
        # Проверяем количество залов
        halls = session.exec(select(Hall)).all()
        halls_data = [{"id": hall.id, "name": hall.name} for hall in halls]
        
        # Проверяем количество переходов
        transitions = session.exec(select(HallTransition)).all()
        transitions_data = []
        
        for transition in transitions[:20]:  # Ограничиваем для читаемости
            from_hall = session.exec(select(Hall).where(Hall.id == transition.from_hall_id)).first()
            to_hall = session.exec(select(Hall).where(Hall.id == transition.to_hall_id)).first()
            transitions_data.append({
                "from_hall": from_hall.name if from_hall else "Unknown",
                "to_hall": to_hall.name if to_hall else "Unknown",
                "transition_time": transition.transition_time
            })
        
        # Проверяем конкретные переходы
        dom_muzyki = session.exec(select(Hall).where(Hall.name.like('%Дом музыки%'))).first()
        tyuz = session.exec(select(Hall).where(Hall.name.like('%ТЮЗ%'))).first()
        
        specific_transitions = {}
        if dom_muzyki and tyuz:
            # Дом музыки → ТЮЗ
            transition1 = session.exec(
                select(HallTransition)
                .where(HallTransition.from_hall_id == dom_muzyki.id)
                .where(HallTransition.to_hall_id == tyuz.id)
            ).first()
            
            if transition1:
                specific_transitions["dom_muzyki_to_tyuz"] = transition1.transition_time
            else:
                specific_transitions["dom_muzyki_to_tyuz"] = "not_found"
            
            # ТЮЗ → Дом музыки
            transition2 = session.exec(
                select(HallTransition)
                .where(HallTransition.from_hall_id == tyuz.id)
                .where(HallTransition.to_hall_id == dom_muzyki.id)
            ).first()
            
            if transition2:
                specific_transitions["tyuz_to_dom_muzyki"] = transition2.transition_time
            else:
                specific_transitions["tyuz_to_dom_muzyki"] = "not_found"
        
        return {
            "total_halls": len(halls),
            "total_transitions": len(transitions),
            "sample_transitions": transitions_data,
            "specific_transitions": specific_transitions,
            "halls_sample": halls_data[:10]  # Первые 10 залов
        }
        
    except Exception as e:
        logger.error(f"Error in debug_transitions: {e}")
        return {"error": str(e)}
    


    
