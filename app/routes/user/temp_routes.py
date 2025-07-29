from fastapi import APIRouter, HTTPException, status, Depends, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database.database import get_session
from models.user import User, UserCreate, TelegramLinkCode
from models.hall import Hall
from models.genre import Genre
from models.concert import Concert
from services.crud import user as UserService
from services.crud import purchase as PurchaseService
from typing import List, Dict
from services.logging.logging import get_logger
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from auth.authenticate import authenticate_cookie
from database.config import get_settings
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime, timedelta
from sqlmodel import select, delete
import os

# Импортируем новые утилиты
from services.user.utils import get_all_festival_days_with_visit_status, group_concerts_by_day

logger = get_logger(logger_name=__name__)

user_route = APIRouter()
hash_password = HashPassword()
settings = get_settings()

# Инициализируем шаблонизатор Jinja2
templates = Jinja2Templates(directory="templates")

user_route = APIRouter(tags=['User'])

@user_route.post('/signup')
async def signup(user: UserCreate, session=Depends(get_session)) -> dict:
    try:
        user_exist = UserService.get_user_by_email(user.email, session)
        
        if user_exist:
            raise HTTPException( 
            status_code=status.HTTP_409_CONFLICT, 
            detail="User with email provided exists already.")
        
        # Создаем пользователя через сервис
        new_user = UserService.create_user(
            session=session,
            email=user.email,
            password=user.password,
            name=user.name,
            role=user.role
        )
        
        return {"message": "User created successfully"}

    except HTTPException:
        # Перебрасываем HTTPException как есть
        raise
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
    
    if hash_password.verify_hash(form_data.password, user_exist.hashed_password):
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
    user = UserService.get_user_by_id(session, id)
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
    bot_link = os.environ.get('BOT_LINK', 'https://t.me/Figaro_FestivalBot')
    logger.info("=== PROFILE PAGE START ===")
    logger.info("=== PROFILE PAGE START ===")
    logger.info("=== PROFILE PAGE START ===")
    logger.info("=== PROFILE PAGE START ===")
    logger.info("=== PROFILE PAGE START ===")
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
        logger.info(f"User external_id type: {type(current_user.external_id)}")
        logger.info(f"User external_id value: {current_user.external_id}")
        
        # Получаем данные о покупках пользователя
        # Используем external_id пользователя для поиска покупок
        user_external_id = current_user.external_id
        
        if not user_external_id:
            # Если у пользователя нет external_id, показываем пустую страницу с базовыми данными
            logger.warning(f"User {current_user.email} has no external_id")
            
            # Создаём базовые данные для шаблона
            basic_route_sheet = {
                "summary": {
                    "total_concerts": 0,
                    "total_days": 0,
                    "total_halls": 0,
                    "total_genres": 0,
                    "total_spent": 0
                },
                "match": {
                    "found": False,
                    "match_type": "no_external_id",
                    "reason": "Для анализа маршрутов требуется external_id",
                    "match_percentage": 0.0,
                    "total_routes_checked": 0,
                    "customer_concerts": [],
                    "best_route": None
                },
                "concerts_by_day": {}
            }
            
            # Для пользователей без external_id не предлагаем привязку к Telegram
            telegram_linked = False
            telegram_id = None
            telegram_username = None
            telegram_link_code = None
            telegram_link_code_expires = None
            
            context = {
                "request": request,
                "user": current_user,
                "concerts": [],
                "purchase_summary": {
                    "total_purchases": 0,
                    "total_spent": 0,
                    "total_concerts": 0,
                    "unique_halls": 0,
                    "genres": []
                },
                "route_sheet": basic_route_sheet,
                "characteristics": {},
                "festival_days": [],
                "telegram_linked": telegram_linked,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username,
                "telegram_link_code": telegram_link_code,
                "telegram_link_code_expires": telegram_link_code_expires,
                "bot_link": bot_link
            }
            return templates.TemplateResponse("profile.html", context)
        
        # Отладочная информация о поиске покупок
        logger.info(f"Searching purchases for external_id: {user_external_id}")
        
        # Получаем уникальные концерты с деталями (исключаем дубликаты от нескольких покупок)
        purchases = PurchaseService.get_user_unique_concerts_with_details(session, user_external_id)
        
        logger.info(f"Found {len(purchases)} purchases for user {user_external_id}")
        
        # Получаем сводную информацию (данные уже уникальные)
        total_spent = sum(p['concert'].get('purchase_count', 1) * (p['concert'].get('price', 0) or 0) for p in purchases)
        purchase_summary = {
            "total_purchases": sum(p['concert'].get('purchase_count', 1) for p in purchases),
            "total_spent": total_spent,
            "total_concerts": len(purchases),  # Уже уникальные концерты
            "unique_halls": len(set(p['concert']['hall']['id'] for p in purchases if p['concert']['hall'])),
            "genres": list(set(p['concert']['genre'] for p in purchases if p['concert']['genre']))
        }
        
        logger.info(f"Purchase summary: {purchase_summary}")
        logger.info(f"Found {len(purchases)} unique concerts")
        
        # Преобразуем данные для шаблона (данные уже уникальные)
        concerts_for_template = []
        for purchase in purchases:
            try:
                # Создаем копию данных концерта
                concert_copy = purchase.copy()
                
                # Добавляем информацию о количестве билетов
                concert_copy['tickets_count'] = purchase['concert'].get('purchase_count', 1)
                concert_copy['total_spent'] = purchase['concert'].get('purchase_count', 1) * (purchase['concert'].get('price', 0) or 0)
                
                # Обрабатываем concert datetime
                if isinstance(purchase['concert']['datetime'], str):
                    concert_copy['concert']['datetime'] = datetime.fromisoformat(purchase['concert']['datetime'])
                else:
                    concert_copy['concert']['datetime'] = purchase['concert']['datetime']
                
                # Преобразуем duration обратно в timedelta
                duration_str = purchase['concert']['duration']
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
                concert_copy = purchase.copy()
                concert_copy['tickets_count'] = purchase['concert'].get('purchase_count', 1)
                concert_copy['total_spent'] = purchase['concert'].get('purchase_count', 1) * (purchase['concert'].get('price', 0) or 0)
                concerts_for_template.append(concert_copy)
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
        
        # Получаем все дни фестиваля с информацией о посещении
        festival_days_data = get_all_festival_days_with_visit_status(session, concerts_for_template)
        
        # Получаем данные для маршрутного листа и характеристик
        if user_external_id:
            # Если есть external_id, получаем полные данные
            try:
                route_sheet_data = get_user_route_sheet(session, user_external_id, concerts_for_template, festival_days_data)
                logger.info(f"Route sheet data: {route_sheet_data}")
                logger.info(f"Concerts by day: {route_sheet_data.get('concerts_by_day', {})}")
            except Exception as e:
                logger.error(f"Error getting route sheet data: {e}")
                route_sheet_data = {
                    "summary": {
                        "total_concerts": len(concerts_for_template),
                        "total_days": 0,
                        "total_halls": 0,
                        "total_genres": 0,
                        "total_spent": 0,
                        "total_concert_time_minutes": 0,
                        "total_walk_time_minutes": 0,
                        "total_distance_km": 0,
                        "unique_compositions": 0,
                        "unique_authors": 0,
                        "unique_artists": 0
                    },
                    "match": {
                        "found": False,
                        "match_type": "error",
                        "reason": f"Ошибка при анализе маршрутов: {str(e)}",
                        "match_percentage": 0.0,
                        "total_routes_checked": 0,
                        "customer_concerts": [],
                        "best_route": None
                    },
                    "concerts_by_day": {}
                }
        
        # Получаем данные для характеристик
        if user_external_id:
            try:
                logger.info(f"[DEBUG] Calling get_user_characteristics with external_id: {user_external_id}")
                characteristics_data = get_user_characteristics(session, user_external_id, concerts_for_template)
                logger.info(f"[DEBUG] get_user_characteristics returned: {characteristics_data}")
            except Exception as e:
                logger.error(f"Error getting characteristics data: {e}")
                characteristics_data = {
                    "total_concerts": 0,
                    "halls": [],
                    "genres": [],
                    "artists": [],
                    "composers": [],
                    "compositions": []
                }
        else:

            # Если нет external_id, создаём базовые данные, но с реальными характеристиками
            logger.info("No external_id, creating basic route sheet and characteristics data")
            
            # Получаем характеристики даже без external_id
            try:
                logger.info(f"Calling get_user_characteristics without external_id")
                characteristics_data = get_user_characteristics(session, None, concerts_for_template)
                logger.info(f"get_user_characteristics returned: {characteristics_data}")
            except Exception as e:
                logger.error(f"Error getting characteristics data without external_id: {e}")
                characteristics_data = {
                    "total_concerts": len(concerts_for_template),
                    "halls": [],
                    "genres": [],
                    "artists": [],
                    "composers": [],
                    "compositions": []
                }
        
        # Создаем маршрутный лист с группировкой по дням и ENRICH-блоком
        try:
            logger.info(f"Creating route sheet without external_id")
            concerts_by_day = group_concerts_by_day(concerts_for_template, festival_days_data)
            logger.info(f"group_concerts_by_day returned: {concerts_by_day}")
            
            # --- ENRICH-БЛОК для пользователей без external_id ---
            concerts_by_day_with_transitions = {}
            for day_index, day_concerts in concerts_by_day.items():
                concerts_with_transitions = []
                for i, concert in enumerate(day_concerts):
                    concert_with_transition = concert.copy()
                    # enrich: переходы
                    if i < len(day_concerts) - 1:
                        next_concert = day_concerts[i + 1]
                        transition_info = calculate_transition_time(session, concert, next_concert)
                        concert_with_transition['transition_info'] = transition_info
                        # enrich: офф-программа между концертами
                        off_program_events = find_available_off_program_events(session, concert, next_concert)
                        concert_with_transition['off_program_events'] = off_program_events
                    else:
                        concert_with_transition['transition_info'] = None
                        concert_with_transition['off_program_events'] = []
                    # enrich: офф-программа до первого концерта
                    if i == 0:
                        before_concert_events = find_available_off_program_events_before_first_concert(session, concert)
                        concert_with_transition['before_concert_events'] = before_concert_events
                    else:
                        concert_with_transition['before_concert_events'] = []
                    # enrich: офф-программа после последнего концерта
                    if i == len(day_concerts) - 1:
                        after_concert_events = find_available_off_program_events_after_last_concert(session, concert)
                        concert_with_transition['after_concert_events'] = after_concert_events
                    else:
                        concert_with_transition['after_concert_events'] = []
                    concerts_with_transitions.append(concert_with_transition)
                concerts_by_day_with_transitions[day_index] = concerts_with_transitions
            # --- КОНЕЦ ENRICH-БЛОКА ---
            
            # Рассчитываем статистику маршрута
            route_stats = calculate_route_statistics(session, concerts_for_template, concerts_by_day_with_transitions)
            
            route_sheet_data = {
                "summary": {
                    "total_concerts": len(concerts_for_template),
                    "total_days": len(concerts_by_day),
                    "total_halls": len(set(c['concert'].get('hall', {}).get('id') for c in concerts_for_template if c['concert'].get('hall'))),
                    "total_genres": len(set(c['concert'].get('genre') for c in concerts_for_template if c['concert'].get('genre'))),
                    "total_spent": sum(c.get('total_spent', 0) for c in concerts_for_template),
                    "total_concert_time_minutes": route_stats.get('total_concert_time_minutes', 0),
                    "total_walk_time_minutes": route_stats.get('total_walk_time_minutes', 0),
                    "total_distance_km": route_stats.get('total_distance_km', 0),
                    "unique_compositions": route_stats.get('unique_compositions', 0),
                    "unique_authors": route_stats.get('unique_authors', 0),
                    "unique_artists": route_stats.get('unique_artists', 0)
                },
                "match": {
                    "found": False,
                    "match_type": "no_external_id",
                    "reason": "Для анализа маршрутов требуется external_id",
                    "match_percentage": 0.0,
                    "total_routes_checked": 0,
                    "customer_concerts": [],
                    "best_route": None
                },
                "concerts_by_day": concerts_by_day_with_transitions
            }
        except Exception as e:
            logger.error(f"Error creating route sheet without external_id: {e}")
            route_sheet_data = {
                "summary": {
                    "total_concerts": len(concerts_for_template),
                    "total_days": 0,
                    "total_halls": 0,
                    "total_genres": 0,
                    "total_spent": sum(c.get('total_spent', 0) for c in concerts_for_template),
                    "total_concert_time_minutes": 0,
                    "total_walk_time_minutes": 0,
                    "total_distance_km": 0,
                    "unique_compositions": 0,
                    "unique_authors": 0,
                    "unique_artists": 0
                },
                "match": {
                    "found": False,
                    "match_type": "no_external_id",
                    "reason": "Для анализа маршрутов требуется external_id",
                    "match_percentage": 0.0,
                    "total_routes_checked": 0,
                    "customer_concerts": [],
                    "best_route": None
                },
                "concerts_by_day": {}
            }
        
        logger.info(f"Festival days data: {festival_days_data}")
        logger.info(f"Characteristics data type: {type(characteristics_data)}")
        logger.info(f"Characteristics data: {characteristics_data}")
        
        # Добавляем статус привязки Telegram (только для пользователей с external_id)
        if user_external_id:
            telegram_linked = current_user.telegram_id is not None
            telegram_id = current_user.telegram_id
            telegram_username = current_user.telegram_username
            # Проверяем, есть ли активный код привязки
            from models.user import TelegramLinkCode
            from sqlmodel import select
            now = datetime.utcnow()
            link_code_obj = session.exec(
                select(TelegramLinkCode)
                .where(TelegramLinkCode.user_id == current_user.id)
                .where(TelegramLinkCode.expires_at > now)
            ).first()
            telegram_link_code = link_code_obj.code if link_code_obj else None
            telegram_link_code_expires = link_code_obj.expires_at if link_code_obj else None
        else:
            # Для пользователей без external_id не предлагаем привязку к Telegram
            telegram_linked = False
            telegram_id = None
            telegram_username = None
            telegram_link_code = None
            telegram_link_code_expires = None
        context = {
            "request": request,
            "user": current_user,
            "concerts": concerts_for_template,  # Изменили название с purchases на concerts
            "purchase_summary": purchase_summary,
            "route_sheet": route_sheet_data,
            "characteristics": characteristics_data,
            "festival_days": festival_days_data,
            "telegram_linked": telegram_linked,
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "telegram_link_code": telegram_link_code,
            "telegram_link_code_expires": telegram_link_code_expires,
            "bot_link": bot_link
        }
        logger.info(f"Route sheet data for template: {route_sheet_data}")
        logger.info(f"Route sheet summary: {route_sheet_data.get('summary', {})}")
        logger.info(f"Route sheet summary keys: {list(route_sheet_data.get('summary', {}).keys())}")
        logger.info(f"Route sheet summary values: {list(route_sheet_data.get('summary', {}).values())}")
        logger.info(f"Context characteristics type: {type(context['characteristics'])}")
        logger.info(f"Context characteristics: {context['characteristics']}")
        logger.info(f"Context characteristics keys: {list(context['characteristics'].keys()) if hasattr(context['characteristics'], 'keys') else 'No keys method'}")
        # Получаем топ композиторов фестиваля
        try:
            user_composers = characteristics_data.get('composers', [])
            top_festival_composers = get_top_festival_composers(session, user_composers, limit=10)
            rare_festival_composers = get_rare_festival_composers(session, user_composers, limit=15)
        except Exception as e:
            logger.error(f"Error getting festival composers: {e}")
            top_festival_composers = []
            rare_festival_composers = []
        
        # Добавляем топ композиторов в контекст
        context["top_festival_composers"] = top_festival_composers
        context["rare_festival_composers"] = rare_festival_composers
        
        return templates.TemplateResponse("profile.html", context)
        
    except Exception as e:
        logger.error(f"Error loading profile page: {str(e)}")
        logger.error(f"Full traceback: ", exc_info=True)
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "email": user.email,
            "external_id": user.external_id,
            "id": user.id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
    


    

def get_user_route_sheet(session, user_external_id: str, concerts_data: list, festival_days_data: list = None) -> dict:
    """
    Получает данные для маршрутного листа пользователя
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (может быть None)
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с данными маршрутного листа
    """
    try:
        from models import Route, CustomerRouteMatch
        from sqlalchemy import select
        
        # Если нет external_id, создаём базовую структуру без анализа маршрутов
        if not user_external_id:
            logger.info("No external_id provided, creating basic route sheet data")
            return {
                "summary": {
                    "total_concerts": len(concerts_data),
                    "total_days": 0,
                    "total_halls": 0,
                    "total_genres": 0,
                    "total_spent": sum(c.get('total_spent', 0) for c in concerts_data)
                },
                "match": {
                    "found": False,
                    "match_type": "no_external_id",
                    "reason": "Для анализа маршрутов требуется external_id",
                    "match_percentage": 0.0,
                    "total_routes_checked": 0,
                    "customer_concerts": [],
                    "best_route": None
                },
                "concerts_by_day": {}
            }
        
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
                            "intellect_category": route.IntellectCategory
                        })
                    
                    # Проверяем частичное совпадение (если есть хотя бы 2 концерта)
                    if len(user_concert_ids) >= 2:
                        common_concerts = set(route_concert_ids) & set(user_concert_ids)
                        if len(common_concerts) >= 2:
                            match_percentage = len(common_concerts) / len(user_concert_ids) * 100
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
                            "match_percentage": match_percentage,
                                "common_concerts": list(common_concerts)
                        })
                        
                except Exception as e:
                    logger.warning(f"Ошибка при анализе маршрута {route.id}: {e}")
                    continue
            
            # Определяем тип соответствия
            if exact_matches:
                match_data = {
                    "found": True,
                    "match_type": "exact",
                    "reason": f"Найдено {len(exact_matches)} точных совпадений",
                    "match_percentage": 100.0,
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": exact_matches[0]  # Берём первый точный матч
                }
            elif partial_matches:
                # Сортируем по проценту совпадения
                partial_matches.sort(key=lambda x: x['match_percentage'], reverse=True)
                best_partial = partial_matches[0]
                match_data = {
                    "found": True,
                    "match_type": "partial",
                    "reason": f"Найдено {len(partial_matches)} частичных совпадений, лучшее: {best_partial['match_percentage']:.1f}%",
                    "match_percentage": best_partial['match_percentage'],
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": {k: v for k, v in best_partial.items() if k != 'match_percentage' and k != 'common_concerts'}
                }
            else:
                match_data = {
                    "found": False,
                    "match_type": "no_match",
                    "reason": "Не найдено подходящих маршрутов",
                    "match_percentage": 0.0,
                    "total_routes_checked": len(all_routes),
                    "customer_concerts": user_concert_ids,
                    "best_route": None
                }
        
        # Группируем концерты по дням
        concerts_by_day = group_concerts_by_day(concerts_data, festival_days_data)
        
        # --- ENRICH-БЛОК (всегда выполняется) ---
        concerts_by_day_with_transitions = {}
        for day_index, day_concerts in concerts_by_day.items():
            concerts_with_transitions = []
            for i, concert in enumerate(day_concerts):
                concert_with_transition = concert.copy()
                # enrich: переходы
                if i < len(day_concerts) - 1:
                    next_concert = day_concerts[i + 1]
                    transition_info = calculate_transition_time(session, concert, next_concert)
                    concert_with_transition['transition_info'] = transition_info
                    # enrich: офф-программа между концертами
                    off_program_events = find_available_off_program_events(session, concert, next_concert)
                    concert_with_transition['off_program_events'] = off_program_events
                else:
                    concert_with_transition['transition_info'] = None
                    concert_with_transition['off_program_events'] = []
                # enrich: офф-программа до первого концерта
                if i == 0:
                    before_concert_events = find_available_off_program_events_before_first_concert(session, concert)
                    concert_with_transition['before_concert_events'] = before_concert_events
                else:
                    concert_with_transition['before_concert_events'] = []
                # enrich: офф-программа после последнего концерта
                if i == len(day_concerts) - 1:
                    after_concert_events = find_available_off_program_events_after_last_concert(session, concert)
                    concert_with_transition['after_concert_events'] = after_concert_events
                else:
                    concert_with_transition['after_concert_events'] = []
                concerts_with_transitions.append(concert_with_transition)
            concerts_by_day_with_transitions[day_index] = concerts_with_transitions
        # --- КОНЕЦ ENRICH-БЛОКА ---
        
        # Рассчитываем статистику маршрута
        route_stats = calculate_route_statistics(session, concerts_data, concerts_by_day_with_transitions)
        
        # Подсчитываем общую статистику
        total_days = len(set(c['concert'].get('date', '').split()[0] for c in concerts_data if c['concert'].get('date')))
        total_halls = len(set(c['concert'].get('hall', {}).get('id') for c in concerts_data if c['concert'].get('hall')))
        total_genres = len(set(c['concert'].get('genre') for c in concerts_data if c['concert'].get('genre')))
        
        return {
            "summary": {
                "total_concerts": len(concerts_data),
                "total_days": total_days,
                "total_halls": total_halls,
                "total_genres": total_genres,
                "total_spent": sum(c['concert'].get('purchase_count', 1) * (c['concert'].get('price', 0) or 0) for c in concerts_data),
                "total_concert_time_minutes": route_stats["total_concert_time_minutes"],
                "total_walk_time_minutes": route_stats["total_walk_time_minutes"],
                "total_distance_km": route_stats["total_distance_km"],
                "unique_compositions": route_stats["unique_compositions"],
                "unique_authors": route_stats["unique_authors"],
                "unique_artists": route_stats["unique_artists"]
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
                "total_spent": sum(c['concert'].get('purchase_count', 1) * (c['concert'].get('price', 0) or 0) for c in concerts_data),
                "total_concert_time_minutes": 0,
                "total_walk_time_minutes": 0,
                "total_distance_km": 0,
                "unique_compositions": 0,
                "unique_authors": 0,
                "unique_artists": 0
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
        
        # Проверяем наложение концертов по времени
        if time_between < 0:
            logger.warning(f"Concert overlap detected: {time_between} minutes (negative)")
            return {
                'time_between': int(time_between),
                'walk_time': 0,
                'status': 'overlap',
                'current_end': current_end.strftime('%H:%M'),
                'next_start': next_start.strftime('%H:%M')
            }
        
        # Если концерты в одном зале, время перехода = 0
        if current_hall_id == next_hall_id:
            logger.info(f"Same hall ({current_hall_id}), no transition needed")
            return {
                'time_between': int(time_between),
                'walk_time': 0,
                'status': 'same_hall'
            }
        
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
        elif walk_time == 0:
            status = 'same_hall'  # В том же зале
        elif walk_time == 1:
            status = 'same_building'  # В том же здании
        elif time_between < walk_time - 3:
            # Если время между концертами меньше времени перехода на 3+ минут - это наложение
            status = 'overlap'  # Наложение из-за недостатка времени на переход
        elif time_between < walk_time:
            # Если разница менее 3 минут - нужно поторопиться
            status = 'hurry'    # Нужно поторопиться
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


def find_available_off_program_events(session, current_concert: dict, next_concert: dict) -> list:
    """
    Находит доступные мероприятия офф-программы между двумя концертами
    
    Args:
        session: Сессия базы данных
        current_concert: Текущий концерт
        next_concert: Следующий концерт
        
    Returns:
        Список доступных мероприятий офф-программы
    """
    try:
        from models import OffProgram, HallTransition, Hall
        from sqlalchemy import select
        from datetime import datetime, timedelta
        
        # Получаем время окончания текущего концерта и начала следующего
        current_start = current_concert['concert'].get('datetime')
        current_duration = current_concert['concert'].get('duration')
        next_start = next_concert['concert'].get('datetime')
        
        if not current_start or not next_start or not current_duration:
            return []
        
        # Вычисляем время окончания текущего концерта
        if hasattr(current_duration, 'total_seconds'):
            current_end = current_start + timedelta(seconds=current_duration.total_seconds())
        else:
            # Если duration - это строка времени
            try:
                time_parts = str(current_duration).split(':')
                if len(time_parts) >= 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    current_end = current_start + timedelta(hours=hours, minutes=minutes)
                else:
                    return []
            except:
                return []
        
        # Получаем ID залов
        current_hall_id = current_concert['concert'].get('hall', {}).get('id')
        next_hall_id = next_concert['concert'].get('hall', {}).get('id')
        
        # Ищем мероприятия офф-программы в промежутке времени
        off_program_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= current_end)
            .where(OffProgram.event_date < next_start)
            .order_by(OffProgram.event_date)
        ).all()
        

        
        available_events = []
        
        for event in off_program_events:
            # Извлекаем SQLModel объект из Row кортежа
            if hasattr(event, '_mapping'):
                event_data = event._mapping['OffProgram']
            elif isinstance(event, tuple) and len(event) > 0:
                event_data = event[0]
            else:
                event_data = event
            
            # Фильтруем только рекомендуемые мероприятия
            if not getattr(event_data, 'recommend', False):
                continue
            
            logger.info(f"Processing event: {event_data.event_name} at {event_data.event_date.strftime('%H:%M')}")
            
            # Вычисляем продолжительность мероприятия
            event_duration = timedelta()
            if event_data.event_long:
                try:
                    time_parts = str(event_data.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        if hours == 0 and minutes == 0:
                            # Если продолжительность 00:00, считаем 30 минут
                            event_duration = timedelta(minutes=30)
                        else:
                            event_duration = timedelta(hours=hours, minutes=minutes)
                    else:
                        event_duration = timedelta(minutes=30)
                except:
                    event_duration = timedelta(minutes=30)  # По умолчанию 30 минут
            else:
                event_duration = timedelta(minutes=30)  # По умолчанию 30 минут
            
            # Вычисляем время окончания мероприятия
            event_end = event_data.event_date + event_duration
            
            # Проверяем, помещается ли мероприятие во временной промежуток
            if event_end <= next_start:
                # Рассчитываем время перехода к мероприятию офф-программы
                walk_time_to_event = 0
                if current_hall_id:
                    # Ищем зал, где проводится мероприятие офф-программы
                    logger.info(f"Looking for event hall: '{event_data.hall_name}'")
                    event_hall = session.exec(
                        select(Hall).where(Hall.name.ilike(f'%{event_data.hall_name}%'))
                    ).first()
                    
                    # Извлекаем SQLModel объект из Row если нужно
                    if hasattr(event_hall, '_mapping'):
                        event_hall = event_hall._mapping['Hall']
                    
                    if event_hall:
                        # Ищем переход от зала концерта к залу мероприятия офф-программы
                        transition_to_event = session.exec(
                            select(HallTransition)
                            .where(HallTransition.from_hall_id == current_hall_id)
                            .where(HallTransition.to_hall_id == event_hall.id)
                        ).first()
                        
                        # Если не найден прямой переход, ищем обратный
                        if not transition_to_event:
                            transition_to_event = session.exec(
                                select(HallTransition)
                                .where(HallTransition.from_hall_id == event_hall.id)
                                .where(HallTransition.to_hall_id == current_hall_id)
                            ).first()
                        
                        if transition_to_event:
                            # Извлекаем время перехода из Row объекта если нужно
                            if hasattr(transition_to_event, '_asdict'):
                                transition_dict = transition_to_event._asdict()
                                if 'HallTransition' in transition_dict:
                                    walk_time_to_event = transition_dict['HallTransition'].transition_time
                                else:
                                    walk_time_to_event = transition_dict.get('transition_time', 0)
                            else:
                                walk_time_to_event = transition_to_event.transition_time
                            logger.info(f"Found transition to event: {current_hall_id} -> {event_hall.id} = {walk_time_to_event} min")
                        else:
                            # Если переход не найден, логируем для диагностики
                            logger.warning(f"No transition found: {current_hall_id} <-> {event_hall.id} (to event)")
                            walk_time_to_event = None  # Явно указываем None для диагностики
                    else:
                        # Если зал мероприятия не найден, логируем для диагностики
                        logger.warning(f"Event hall not found: {event_data.hall_name}")
                        walk_time_to_event = None  # Явно указываем None для диагностики
                
                # Рассчитываем время перехода от мероприятия офф-программы к следующему концерту
                walk_time_from_event = 0
                if next_hall_id:
                    # Ищем зал, где проводится мероприятие офф-программы
                    logger.info(f"Looking for event hall: '{event_data.hall_name}'")
                    event_hall = session.exec(
                        select(Hall).where(Hall.name.ilike(f'%{event_data.hall_name}%'))
                    ).first()
                    
                    # Извлекаем SQLModel объект из Row если нужно
                    if hasattr(event_hall, '_mapping'):
                        event_hall = event_hall._mapping['Hall']
                    
                    if event_hall:
                        # Ищем переход от зала мероприятия офф-программы к залу следующего концерта
                        transition_from_event = session.exec(
                            select(HallTransition)
                            .where(HallTransition.from_hall_id == event_hall.id)
                            .where(HallTransition.to_hall_id == next_hall_id)
                        ).first()
                        
                        # Если не найден прямой переход, ищем обратный
                        if not transition_from_event:
                            transition_from_event = session.exec(
                                select(HallTransition)
                                .where(HallTransition.from_hall_id == next_hall_id)
                                .where(HallTransition.to_hall_id == event_hall.id)
                            ).first()
                        
                        if transition_from_event:
                            # Извлекаем время перехода из Row объекта если нужно
                            if hasattr(transition_from_event, '_asdict'):
                                transition_dict = transition_from_event._asdict()
                                if 'HallTransition' in transition_dict:
                                    walk_time_from_event = transition_dict['HallTransition'].transition_time
                                else:
                                    walk_time_from_event = transition_dict.get('transition_time', 0)
                            else:
                                walk_time_from_event = transition_from_event.transition_time
                            logger.info(f"Found transition from event: {event_hall.id} -> {next_hall_id} = {walk_time_from_event} min")
                        else:
                            # Если переход не найден, логируем для диагностики
                            logger.warning(f"No transition found: {event_hall.id} <-> {next_hall_id} (from event)")
                            walk_time_from_event = None  # Явно указываем None для диагностики
                    else:
                        # Если зал мероприятия не найден, логируем для диагностики
                        logger.warning(f"Event hall not found: {event_data.hall_name}")
                        walk_time_from_event = None  # Явно указываем None для диагностики
                
                # Проверяем, достаточно ли времени на переходы
                # Обрабатываем None значения для диагностики
                if walk_time_to_event is None:
                    logger.warning(f"Cannot calculate total walk time: walk_time_to_event is None")
                    total_walk_time = None
                elif walk_time_from_event is None:
                    logger.warning(f"Cannot calculate total walk time: walk_time_from_event is None")
                    total_walk_time = None
                else:
                    total_walk_time = walk_time_to_event + walk_time_from_event
                
                available_time = (next_start - current_end).total_seconds() / 60
                event_duration_minutes = event_duration.total_seconds() / 60
                
                # Проверяем доступность только если у нас есть данные о переходах
                if total_walk_time is not None and total_walk_time + event_duration_minutes <= available_time:
                    # Форматируем продолжительность для отображения
                    duration_display = ""
                    if event_duration.total_seconds() > 0:
                        hours = int(event_duration.total_seconds() // 3600)
                        minutes = int((event_duration.total_seconds() % 3600) // 60)
                        if hours > 0 and minutes > 0:
                            duration_display = f"{hours}ч {minutes}м"
                        elif hours > 0:
                            duration_display = f"{hours}ч"
                        else:
                            duration_display = f"{minutes}м"
                    else:
                        duration_display = "30м"  # По умолчанию
                    
                    available_events.append({
                        'id': event_data.id,
                        'event_num': event_data.event_num,
                        'event_name': event_data.event_name,
                        'description': event_data.description,
                        'event_date': event_data.event_date,
                        'event_date_display': event_data.event_date.strftime('%H:%M'),
                        'duration': duration_display,
                        'hall_name': event_data.hall_name,
                        'format': event_data.format.value if event_data.format else 'Не указан',
                        'recommend': event_data.recommend,
                        'link': event_data.link,
                        'walk_time_to_event': walk_time_to_event,
                        'walk_time_from_event': walk_time_from_event,
                        'total_walk_time': total_walk_time,
                        'available_time': int(available_time),
                        'event_duration_minutes': int(event_duration_minutes)
                    })
        
        # Сортируем по времени начала
        available_events.sort(key=lambda x: x['event_date'])
        
        return available_events
        
    except Exception as e:
        logger.error(f"Error finding available off program events: {e}")
        import traceback
        print(f"DEBUG: Full error traceback:")
        traceback.print_exc()
        return []


def find_available_off_program_events_before_first_concert(session, first_concert: dict) -> list:
    """
    Находит доступные мероприятия офф-программы до первого концерта дня
    
    Args:
        session: Сессия базы данных
        first_concert: Первый концерт дня
        
    Returns:
        Список доступных мероприятий офф-программы
    """
    try:
        from models import OffProgram, HallTransition, Hall
        from sqlalchemy import select
        from datetime import datetime, timedelta
        
        # Получаем время начала первого концерта
        concert_start = first_concert['concert'].get('datetime')
        
        if not concert_start:
            return []
        
        # Определяем временное окно для поиска (например, за 4 часа до концерта)
        search_start = concert_start - timedelta(hours=4)
        
        logger.info(f"Searching off-program events before concert: {concert_start.strftime('%H:%M')}")
        logger.info(f"Search window: {search_start.strftime('%H:%M')} - {concert_start.strftime('%H:%M')}")
        
        # Ищем мероприятия офф-программы до концерта
        off_program_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= search_start)
            .where(OffProgram.event_date < concert_start)
            .order_by(OffProgram.event_date)  # Сортируем по возрастанию времени
        ).all()
        
        logger.info(f"Found {len(off_program_events)} off-program events in search window")
        
        available_events = []
        
        for event in off_program_events:
            # Извлекаем SQLModel объект из Row кортежа
            if hasattr(event, '_mapping'):
                event_data = event._mapping['OffProgram']
            elif isinstance(event, tuple) and len(event) > 0:
                event_data = event[0]
            else:
                event_data = event
            
            logger.info(f"Processing event: {event_data.event_name} at {event_data.event_date.strftime('%H:%M')}")
            
            # Вычисляем продолжительность мероприятия
            event_duration = timedelta()
            if event_data.event_long:
                try:
                    time_parts = str(event_data.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        if hours == 0 and minutes == 0:
                            event_duration = timedelta(minutes=30)
                        else:
                            event_duration = timedelta(hours=hours, minutes=minutes)
                    else:
                        event_duration = timedelta(minutes=30)
                except:
                    event_duration = timedelta(minutes=30)
            else:
                event_duration = timedelta(minutes=30)
            
            # Вычисляем время окончания мероприятия
            event_end = event_data.event_date + event_duration
            
            logger.info(f"Event duration: {event_duration}, Event end: {event_end.strftime('%H:%M')}")
            
            # Проверяем, что мероприятие заканчивается до начала концерта
            if event_end <= concert_start:
                logger.info(f"Event ends before concert, checking transition time...")
                
                # Рассчитываем время перехода от мероприятия к концерту
                walk_time_to_concert = 0
                concert_hall_id = first_concert['concert'].get('hall', {}).get('id')
                
                if concert_hall_id:
                    # Ищем зал, где проводится мероприятие офф-программы
                    event_hall = session.exec(
                        select(Hall).where(Hall.name.ilike(f'%{event_data.hall_name}%'))
                    ).first()
                    
                    # Извлекаем SQLModel объект из Row если нужно
                    if hasattr(event_hall, '_mapping'):
                        event_hall = event_hall._mapping['Hall']
                    
                    if event_hall:
                        logger.info(f"Found event hall: {event_hall.name} (ID: {event_hall.id})")
                        
                        # Ищем переход от зала мероприятия к залу концерта
                        transition = session.exec(
                            select(HallTransition)
                            .where(HallTransition.from_hall_id == event_hall.id)
                            .where(HallTransition.to_hall_id == concert_hall_id)
                        ).first()
                        
                        # Если не найден прямой переход, ищем обратный
                        if not transition:
                            transition = session.exec(
                                select(HallTransition)
                                .where(HallTransition.from_hall_id == concert_hall_id)
                                .where(HallTransition.to_hall_id == event_hall.id)
                            ).first()
                        
                        if transition:
                            # Извлекаем время перехода из Row объекта если нужно
                            if hasattr(transition, '_asdict'):
                                transition_dict = transition._asdict()
                                if 'HallTransition' in transition_dict:
                                    walk_time_to_concert = transition_dict['HallTransition'].transition_time
                                else:
                                    walk_time_to_concert = transition_dict.get('transition_time', 0)
                            else:
                                walk_time_to_concert = transition.transition_time
                            logger.info(f"Found transition time: {walk_time_to_concert} minutes")
                        else:
                            walk_time_to_concert = 5  # Значение по умолчанию
                            logger.info(f"No transition found, using default: {walk_time_to_concert} minutes")
                    else:
                        logger.warning(f"Event hall not found for: {event_data.hall_name}")
                
                # Проверяем, достаточно ли времени для перехода
                available_time = (concert_start - event_end).total_seconds() / 60
                
                logger.info(f"Available time: {available_time} minutes, Walk time: {walk_time_to_concert} minutes")
                
                if walk_time_to_concert <= available_time:
                    logger.info(f"Event fits in available time, adding to results")
                    
                    # Форматируем продолжительность для отображения
                    duration_display = ""
                    if event_duration.total_seconds() > 0:
                        hours = int(event_duration.total_seconds() // 3600)
                        minutes = int((event_duration.total_seconds() % 3600) // 60)
                        if hours > 0 and minutes > 0:
                            duration_display = f"{hours}ч {minutes}м"
                        elif hours > 0:
                            duration_display = f"{hours}ч"
                        else:
                            duration_display = f"{minutes}м"
                    else:
                        duration_display = "30м"
                    
                    available_events.append({
                        'id': event_data.id,
                        'event_num': event_data.event_num,
                        'event_name': event_data.event_name,
                        'description': event_data.description,
                        'event_date': event_data.event_date,
                        'event_date_display': event_data.event_date.strftime('%H:%M'),
                        'duration': duration_display,
                        'hall_name': event_data.hall_name,
                        'format': event_data.format.value if event_data.format else 'Не указан',
                        'recommend': event_data.recommend,
                        'link': event_data.link,
                        'walk_time_to_concert': walk_time_to_concert,
                        'available_time': int(available_time),
                        'event_duration_minutes': int(event_duration.total_seconds() / 60),
                        'type': 'before_concert'
                    })
                else:
                    logger.info(f"Event does not fit in available time")
            else:
                logger.info(f"Event ends after concert start, skipping")
        
        # Сортируем: сначала рекомендуемые, затем по времени начала (по возрастанию)
        available_events.sort(key=lambda x: (-x['recommend'], x['event_date']))
        
        return available_events
        
    except Exception as e:
        logger.error(f"Error finding available off program events before first concert: {e}")
        return []


def find_available_off_program_events_after_last_concert(session, last_concert: dict) -> list:
    """
    Находит доступные мероприятия офф-программы после последнего концерта дня
    
    Args:
        session: Сессия базы данных
        last_concert: Последний концерт дня
        
    Returns:
        Список доступных мероприятий офф-программы
    """
    try:
        from models import OffProgram, HallTransition, Hall
        from sqlalchemy import select
        from datetime import datetime, timedelta
        
        # Получаем время окончания последнего концерта
        concert_start = last_concert['concert'].get('datetime')
        concert_duration = last_concert['concert'].get('duration')
        
        if not concert_start or not concert_duration:
            return []
        
        # Вычисляем время окончания концерта
        if hasattr(concert_duration, 'total_seconds'):
            concert_end = concert_start + timedelta(seconds=concert_duration.total_seconds())
        else:
            # Если duration - это строка времени
            try:
                time_parts = str(concert_duration).split(':')
                if len(time_parts) >= 2:
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    concert_end = concert_start + timedelta(hours=hours, minutes=minutes)
                else:
                    return []
            except:
                return []
        
        # Определяем временное окно для поиска (например, до 22:00)
        search_end = datetime.combine(concert_end.date(), datetime.max.time().replace(hour=22, minute=0))
        
        # Ищем мероприятия офф-программы после концерта
        off_program_events = session.exec(
            select(OffProgram)
            .where(OffProgram.event_date >= concert_end)
            .where(OffProgram.event_date <= search_end)
            .order_by(OffProgram.event_date)
        ).all()
        
        available_events = []
        
        for event in off_program_events:
            # Извлекаем SQLModel объект из Row кортежа
            if hasattr(event, '_mapping'):
                event_data = event._mapping['OffProgram']
            elif isinstance(event, tuple) and len(event) > 0:
                event_data = event[0]
            else:
                event_data = event
            
            # Вычисляем продолжительность мероприятия
            event_duration = timedelta()
            if event_data.event_long:
                try:
                    time_parts = str(event_data.event_long).split(':')
                    if len(time_parts) >= 2:
                        hours = int(time_parts[0])
                        minutes = int(time_parts[1])
                        if hours == 0 and minutes == 0:
                            event_duration = timedelta(minutes=30)
                        else:
                            event_duration = timedelta(hours=hours, minutes=minutes)
                    else:
                        event_duration = timedelta(minutes=30)
                except:
                    event_duration = timedelta(minutes=30)
            else:
                event_duration = timedelta(minutes=30)
            
            # Вычисляем время окончания мероприятия
            event_end = event_data.event_date + event_duration
            
            # Проверяем, что мероприятие помещается во временное окно
            if event_end <= search_end:
                # Рассчитываем время перехода от концерта к мероприятию
                walk_time_from_concert = 0
                concert_hall_id = last_concert['concert'].get('hall', {}).get('id')
                
                if concert_hall_id:
                    # Ищем зал, где проводится мероприятие офф-программы
                    event_hall = session.exec(
                        select(Hall).where(Hall.name.ilike(f'%{event_data.hall_name}%'))
                    ).first()
                    
                    # Извлекаем SQLModel объект из Row если нужно
                    if hasattr(event_hall, '_mapping'):
                        event_hall = event_hall._mapping['Hall']
                    
                    if event_hall:
                        # Ищем переход от зала концерта к залу мероприятия
                        transition = session.exec(
                            select(HallTransition)
                            .where(HallTransition.from_hall_id == concert_hall_id)
                            .where(HallTransition.to_hall_id == event_hall.id)
                        ).first()
                        
                        # Если не найден прямой переход, ищем обратный
                        if not transition:
                            transition = session.exec(
                                select(HallTransition)
                                .where(HallTransition.from_hall_id == event_hall.id)
                                .where(HallTransition.to_hall_id == concert_hall_id)
                            ).first()
                        
                        if transition:
                            # Извлекаем время перехода из Row объекта если нужно
                            if hasattr(transition, '_asdict'):
                                transition_dict = transition._asdict()
                                if 'HallTransition' in transition_dict:
                                    walk_time_from_concert = transition_dict['HallTransition'].transition_time
                                else:
                                    walk_time_from_concert = transition_dict.get('transition_time', 0)
                            else:
                                walk_time_from_concert = transition.transition_time
                        else:
                            walk_time_from_concert = 5  # Значение по умолчанию
                
                # Проверяем, достаточно ли времени для перехода
                available_time = (event_data.event_date - concert_end).total_seconds() / 60
                
                if walk_time_from_concert <= available_time:
                    # Форматируем продолжительность для отображения
                    duration_display = ""
                    if event_duration.total_seconds() > 0:
                        hours = int(event_duration.total_seconds() // 3600)
                        minutes = int((event_duration.total_seconds() % 3600) // 60)
                        if hours > 0 and minutes > 0:
                            duration_display = f"{hours}ч {minutes}м"
                        elif hours > 0:
                            duration_display = f"{hours}ч"
                        else:
                            duration_display = f"{minutes}м"
                    else:
                        duration_display = "30м"
                    
                    available_events.append({
                        'id': event_data.id,
                        'event_num': event_data.event_num,
                        'event_name': event_data.event_name,
                        'description': event_data.description,
                        'event_date': event_data.event_date,
                        'event_date_display': event_data.event_date.strftime('%H:%M'),
                        'duration': duration_display,
                        'hall_name': event_data.hall_name,
                        'format': event_data.format.value if event_data.format else 'Не указан',
                        'recommend': event_data.recommend,
                        'link': event_data.link,
                        'walk_time_from_concert': walk_time_from_concert,
                        'available_time': int(available_time),
                        'event_duration_minutes': int(event_duration.total_seconds() / 60),
                        'type': 'after_concert'
                    })
        
        # Сортируем по времени начала
        available_events.sort(key=lambda x: x['event_date'])
        
        return available_events
        
    except Exception as e:
        logger.error(f"Error finding available off program events after last concert: {e}")
        return []


# Функции group_concerts_by_day и get_all_festival_days_with_visit_status 
# перенесены в app/services/user/utils/


def get_user_characteristics(session, user_external_id: str, concerts_data: list) -> dict:
    """
    Получает характеристики пользователя на основе его покупок
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с характеристиками пользователя
    """
    from collections import defaultdict, Counter
    
    logger.info(f"=== DEBUG: Called get_user_characteristics #1 (line 1820) ===")
    logger.info(f"user_external_id: {user_external_id}")
    logger.info(f"concerts_data length: {len(concerts_data)}")
    
    # Дополнительная отладка структуры данных
    if concerts_data:
        sample_concert = concerts_data[0]['concert']
        logger.info(f"Sample concert structure: {list(sample_concert.keys())}")
        if 'compositions' in sample_concert:
            logger.info(f"Sample concert has {len(sample_concert['compositions'])} compositions")
            if sample_concert['compositions']:
                sample_composition = sample_concert['compositions'][0]
                logger.info(f"Sample composition structure: {sample_composition}")
    
    if not concerts_data:
        return {
            "total_concerts": 0,
            "halls": [],
            "genres": [],
            "artists": [],
            "composers": [],
            "compositions": []
        }
    
    # Получаем все залы и жанры с отметкой о посещении
    logger.info(f"[DEBUG] About to call get_all_halls_and_genres_with_visit_status with user_external_id={user_external_id}")
    logger.info(f"[DEBUG] concerts_data length: {len(concerts_data)}")
    try:
        halls_and_genres = get_all_halls_and_genres_with_visit_status(session, user_external_id, concerts_data)
        logger.info(f"[DEBUG] get_all_halls_and_genres_with_visit_status returned: {halls_and_genres}")
    except Exception as e:
        logger.error(f"[ERROR] Exception in get_all_halls_and_genres_with_visit_status: {e}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        halls_and_genres = {"halls": [], "genres": []}
    
    logger.info(f"[DEBUG] After get_all_halls_and_genres_with_visit_status, halls_and_genres: {halls_and_genres}")
    
    # Счетчики для различных характеристик
    artists_counter = Counter()
    composers_counter = Counter()
    compositions_counter = Counter()
    
    # Словари для хранения номеров концертов
    artists_concerts = defaultdict(list)
    composers_concerts = defaultdict(list)
    compositions_concerts = defaultdict(list)
    
    # Обрабатываем каждый концерт
    for concert_data in concerts_data:
        concert = concert_data['concert']
        
        # Используем данные, которые уже загружены в concert_data
        try:
            # Артисты (уже загружены в данных)
            if 'artists' in concert:
                for artist in concert['artists']:
                    artists_counter[artist['name']] += 1
                    # Сохраняем ID концерта для артиста
                    concert_id = concert.get('id', 0)
                    if concert_id > 0:
                        artists_concerts[artist['name']].append(concert_id)
                    logger.debug(f"Found artist: {artist['name']} for concert {concert['id']}")
            
            # Композиции и их авторы (уже загружены в данных)
            if 'compositions' in concert:
                for composition in concert['compositions']:
                    # Формируем ключ для композиции с автором
                    if 'author' in composition and composition['author'] and composition['author']['name'] != '_Прочее':
                        composition_key = f"{composition['name']} ({composition['author']['name']})"
                        composers_counter[composition['author']['name']] += 1
                        logger.debug(f"Found composer: {composition['author']['name']} for composition {composition['name']}")
                    else:
                        # Логируем случаи с "_Прочее" или отсутствующим автором
                        if 'author' in composition and composition['author'] and composition['author']['name'] == '_Прочее':
                            logger.debug(f"Skipping composer '_Прочее' for composition {composition['name']}")
                        composition_key = f"{composition['name']} (Автор неизвестен)"
                    
                    compositions_counter[composition_key] += 1
                    # Сохраняем ID концерта для произведения
                    concert_id = concert.get('id', 0)
                    if concert_id > 0:
                        compositions_concerts[composition_key].append(concert_id)
                    logger.debug(f"Found composition: {composition_key} for concert {concert['id']}")
                    
                    # Сохраняем ID концерта для композитора
                    if 'author' in composition and composition['author'] and composition['author']['name'] != '_Прочее':
                        if concert_id > 0:
                            composers_concerts[composition['author']['name']].append(concert_id)
                
        except Exception as e:
            logger.warning(f"Error processing concert data for {concert['id']}: {e}")
            continue
    
    # Преобразуем счетчики в списки с сортировкой по количеству
    def counter_to_list(counter, limit=None, concerts_dict=None):
        items = counter.most_common()
        if limit is not None:
            items = items[:limit]
        
        result = []
        for name, count in items:
            item = {"name": name, "count": count}
            if concerts_dict and name in concerts_dict:
                item["concerts"] = sorted(concerts_dict[name])
            result.append(item)
        return result
    
    characteristics = {
        "total_concerts": len(concerts_data),
        "halls": halls_and_genres["halls"],
        "genres": halls_and_genres["genres"],
        "artists": counter_to_list(artists_counter, None, artists_concerts),  # Показываем всех артистов с номерами концертов
        "composers": counter_to_list(composers_counter, None, composers_concerts),  # Показываем всех композиторов с номерами концертов
        "compositions": counter_to_list(compositions_counter, None, compositions_concerts)  # Показываем все произведения с номерами концертов
    }
    
    # Логирование результатов
    logger.info(f"Characteristics calculation results:")
    logger.info(f"  Total concerts: {len(concerts_data)}")
    logger.info(f"  Artists found: {len(artists_counter)}")
    logger.info(f"  Composers found: {len(composers_counter)}")
    logger.info(f"  Compositions found: {len(compositions_counter)}")
    logger.info(f"  Top composers: {[name for name, count in composers_counter.most_common(5)]}")
    
    return characteristics
    

def get_rare_festival_composers(session, user_composers: list = None, limit: int = 15) -> list:
    """
    Получает редких композиторов фестиваля по количеству произведений (с наименьшим количеством)
    
    Args:
        session: Сессия базы данных
        user_composers: Список композиторов пользователя для проверки активности
        limit: Количество редких композиторов для отображения
        
    Returns:
        Список редких композиторов с количеством произведений и статусом активности
    """
    from models.concert import Concert
    from models.composition import Composition, Author, ConcertCompositionLink
    from sqlmodel import select
    from collections import Counter
    
    # Получаем все концерты с композициями
    all_concerts = session.exec(select(Concert)).all()
    
    # Счетчик композиторов
    composers_counter = Counter()
    
    # Обрабатываем каждый концерт
    for concert in all_concerts:
        try:
            # Получаем композиции для концерта напрямую через SQL
            compositions = session.exec(
                select(Composition, Author)
                .join(Author, Composition.author_id == Author.id)
                .join(ConcertCompositionLink, Composition.id == ConcertCompositionLink.composition_id)
                .where(ConcertCompositionLink.concert_id == concert.id)
            ).all()
            
            # Композиции и их авторы
            for composition, author in compositions:
                if author and author.name != '_Прочее':
                    composers_counter[author.name] += 1
                    logger.debug(f"Found composer: {author.name} for composition {composition.name} in concert {concert.id}")
        except Exception as e:
            logger.warning(f"Error getting concert compositions for {concert.id}: {e}")
            continue
    
    # Создаем список имен композиторов пользователя для быстрой проверки
    user_composer_names = set()
    if user_composers:
        user_composer_names = {composer['name'] for composer in user_composers}
    
    # Получаем всех композиторов, отсортированных по количеству произведений (от меньшего к большему)
    all_composers_sorted = composers_counter.most_common()
    all_composers_sorted.reverse()  # Инвертируем для получения редких композиторов
    
    # Фильтруем композиторов, исключая "_Прочее"
    filtered_composers = [(name, count) for name, count in all_composers_sorted if name != "_Прочее"]
    
    # Берем только редких композиторов
    rare_composers = []
    for name, count in filtered_composers[:limit]:
        is_active = name in user_composer_names
        rare_composers.append({
            "name": name, 
            "count": count, 
            "is_active": is_active
        })
    
    return rare_composers


def get_top_festival_composers(session, user_composers: list = None, limit: int = 5) -> list:
    """
    Получает топ композиторов фестиваля по количеству произведений
    
    Args:
        session: Сессия базы данных
        user_composers: Список композиторов пользователя для проверки активности
        
    Returns:
        Список топ композиторов с количеством произведений и статусом активности
    """
    from models.concert import Concert
    from models.composition import Composition, Author
    from sqlmodel import select
    from collections import Counter
    
    # Получаем все концерты с композициями
    all_concerts = session.exec(select(Concert)).all()
    
    # Счетчик композиторов
    composers_counter = Counter()
    
    # Обрабатываем каждый концерт
    for concert in all_concerts:
        try:
            # Принудительно загружаем связи
            session.refresh(concert)
            
            # Композиции и их авторы
            for composition in concert.compositions:
                if composition.author:
                    composers_counter[composition.author.name] += 1
                    
        except Exception as e:
            logger.warning(f"Error getting concert compositions for {concert.id}: {e}")
            continue
    
    # Создаем список имен композиторов пользователя для быстрой проверки
    user_composer_names = set()
    if user_composers:
        user_composer_names = {composer['name'] for composer in user_composers}
    
    # Получаем всех композиторов, отсортированных по количеству произведений
    all_composers_sorted = composers_counter.most_common()
    
    # Фильтруем композиторов, исключая "_Прочее"
    filtered_composers = [(name, count) for name, count in all_composers_sorted if name != "_Прочее"]
    
    # Добавляем отладочную информацию
    logger.info(f"All composers sorted: {all_composers_sorted[:15]}")
    logger.info(f"Filtered composers: {filtered_composers[:15]}")
    
    # Определяем позиции с учетом равных мест (топ-5)
    top_composers = []
    current_position = 1
    current_count = None
    
    # Проходим по всем композиторам, чтобы найти тех, кто должен быть в топ-5
    for i, (name, count) in enumerate(filtered_composers):
        # Если это первый элемент или количество изменилось, обновляем позицию
        if current_count is None or count != current_count:
            # Для первого элемента позиция 1, для остальных увеличиваем на 1
            current_position = 1 if current_count is None else current_position + 1
            current_count = count
        
        # Добавляем композитора, если его позиция <= limit
        if current_position <= limit:
            logger.info(f"Position {current_position}: {name} - {count} compositions")
            
            is_active = name in user_composer_names
            top_composers.append({
                "name": name, 
                "count": count, 
                "is_active": is_active,
                "position": current_position
            })
        else:
            # Если позиция больше limit, прекращаем
            break
    
    return top_composers

    

def calculate_route_statistics(session, concerts_data: list, concerts_by_day_with_transitions: dict) -> dict:
    """
    Рассчитывает дополнительную статистику маршрута
    
    Args:
        concerts_data: Список концертов пользователя
        concerts_by_day_with_transitions: Концерты сгруппированные по дням с переходами
        
    Returns:
        Словарь с дополнительной статистикой
    """
    from datetime import timedelta
    
    # Общее время концертов
    total_concert_time = 0
    for concert in concerts_data:
        duration = concert['concert'].get('duration')
        if duration:
            if hasattr(duration, 'total_seconds'):
                total_concert_time += duration.total_seconds() / 60  # в минутах
            elif isinstance(duration, timedelta):
                total_concert_time += duration.total_seconds() / 60
            else:
                # Предполагаем 90 минут если нет данных
                total_concert_time += 90
    
    # Общее время переходов между залами
    total_walk_time = 0
    total_distance_km = 0  # 5 км/ч = 83.33 м/мин
    
    for day_concerts in concerts_by_day_with_transitions.values():
        for concert in day_concerts:
            if concert.get('transition_info') and concert['transition_info'].get('walk_time'):
                walk_time = concert['transition_info']['walk_time']
                if walk_time and walk_time > 0:
                    total_walk_time += walk_time
                    # Рассчитываем расстояние: 5 км/ч = 83.33 м/мин
                    distance_km = (walk_time * 83.33) / 1000
                    total_distance_km += distance_km
    
    # Количество уникальных произведений и авторов
    unique_compositions = set()
    unique_authors = set()
    unique_artists = set()
    
    for concert in concerts_data:
        # Получаем детали концерта из базы данных
        try:
            from models.concert import Concert
            from sqlmodel import select
            
            # Получаем концерт с загруженными связями
            db_concert = session.exec(select(Concert).where(Concert.id == concert['concert']['id'])).first()
            
            if db_concert:
                # Принудительно загружаем связи
                session.refresh(db_concert)
                
                # Артисты
                for artist in db_concert.artists:
                    unique_artists.add(artist.name)
                
                # Композиции и их авторы
                for composition in db_concert.compositions:
                    unique_compositions.add(composition.name)
                    if composition.author:
                        unique_authors.add(composition.author.name)
                
        except Exception as e:
            logger.warning(f"Error getting concert details for statistics: {e}")
            continue
    
    return {
        "total_concert_time_minutes": int(total_concert_time),
        "total_walk_time_minutes": int(total_walk_time),
        "total_distance_km": round(total_distance_km, 1),
        "unique_compositions": len(unique_compositions),
        "unique_authors": len(unique_authors),
        "unique_artists": len(unique_artists)
    }


def get_all_halls_and_genres_with_visit_status(session, user_external_id: str, concerts_data: list) -> dict:
    """
    Получает все залы и жанры с отметкой о посещении пользователем
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя (может быть None)
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с залами и жанрами и их статусом посещения
    """
    logger.info(f"[DEBUG] ENTERING get_all_halls_and_genres_with_visit_status")
    logger.info(f"[DEBUG] user_external_id: {user_external_id}")
    logger.info(f"[DEBUG] concerts_data length: {len(concerts_data)}")
    
    from collections import Counter, defaultdict
    
    logger.info(f"[DEBUG] get_all_halls_and_genres_with_visit_status called with {len(concerts_data)} concerts")
    
    try:
        # Получаем все концерты фестиваля для определения жанров и залов
        logger.info("[DEBUG] Fetching all concerts from database...")
        all_concerts = session.exec(select(Concert)).all()
        logger.info(f"[DEBUG] Found {len(all_concerts)} concerts in database")
        
        # Собираем все уникальные жанры и залы из концертов фестиваля
        all_genres = set()
        festival_halls = set()
        for concert in all_concerts:
            if concert.genre:
                all_genres.add(concert.genre)
            if concert.hall and concert.hall.name:
                festival_halls.add(concert.hall.name)
        
        logger.info(f"[DEBUG] Festival halls from concerts: {festival_halls}")
        logger.info(f"[DEBUG] All festival genres: {all_genres}")
        
        # Используем только залы, где проходят концерты фестиваля
        all_halls = festival_halls
        
        logger.info(f"[DEBUG] All festival genres: {all_genres}")
        logger.info(f"[DEBUG] All festival halls: {all_halls}")
        
        # Счетчики посещений залов и жанров пользователем
        halls_counter = Counter()
        genres_counter = Counter()
        halls_concerts = defaultdict(list)  # Для хранения номеров концертов залов
        genres_concerts = defaultdict(list)  # Для хранения номеров концертов жанров
        
        # Обрабатываем концерты пользователя
        logger.info(f"[DEBUG] Processing {len(concerts_data)} user concerts...")
        for concert_data in concerts_data:
            concert = concert_data['concert']
            concert_id = concert.get('id', 0)
            
            # Добавляем зал в счетчик
            if concert.get('hall') and concert['hall'].get('name'):
                halls_counter[concert['hall']['name']] += 1
                if concert_id > 0:
                    halls_concerts[concert['hall']['name']].append(concert_id)
            
            # Добавляем жанр в счетчик
            if concert.get('genre'):
                genres_counter[concert['genre']] += 1
                if concert_id > 0:
                    genres_concerts[concert['genre']].append(concert_id)
        
        logger.info(f"[DEBUG] User halls counter: {dict(halls_counter)}")
        logger.info(f"[DEBUG] User genres counter: {dict(genres_counter)}")
        
        # Формируем список ВСЕХ залов с количеством посещений
        halls_with_status = []
        for hall_name in all_halls:
            visit_count = halls_counter.get(hall_name, 0)
            hall_data = {
                "name": hall_name,
                "visit_count": visit_count,
                "is_visited": visit_count > 0,
                "address": "",  # Адрес не доступен из данных концертов
                "seats": 0      # Количество мест не доступно из данных концертов
            }
            if hall_name in halls_concerts:
                hall_data["concerts"] = sorted(halls_concerts[hall_name])
            halls_with_status.append(hall_data)
        
        # Сортируем залы: сначала посещенные (по убыванию), потом непосещенные
        halls_with_status.sort(key=lambda x: (x['is_visited'], x['visit_count']), reverse=True)
        
        # Формируем список ВСЕХ жанров с количеством посещений
        genres_with_status = []
        for genre in all_genres:
            visit_count = genres_counter.get(genre, 0)
            genre_data = {
                "name": genre,
                "visit_count": visit_count,
                "is_visited": visit_count > 0
            }
            if genre in genres_concerts:
                genre_data["concerts"] = sorted(genres_concerts[genre])
            genres_with_status.append(genre_data)
        
        # Сортируем жанры: сначала посещенные (по убыванию), потом непосещенные
        genres_with_status.sort(key=lambda x: (x['is_visited'], x['visit_count']), reverse=True)
        
        logger.info(f"[DEBUG] Returning halls: {len(halls_with_status)}, genres: {len(genres_with_status)}")
        
        return {
            "halls": halls_with_status,
            "genres": genres_with_status
        }
        
    except Exception as e:
        logger.error(f"[ERROR] Exception in get_all_halls_and_genres_with_visit_status: {e}")
        logger.error(f"[ERROR] Exception type: {type(e)}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {
            "halls": [],
            "genres": []
        }


@user_route.post("/telegram/link-code")
async def generate_telegram_link_code(request: Request, session=Depends(get_session)):
    """
    Генерирует уникальный код для привязки Telegram-аккаунта. Требует авторизации пользователя.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user_email = await authenticate_cookie(token)
    if not user_email:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    user = UserService.get_user_by_email(user_email, session)
    if not user:
        return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=404)
    # Удаляем старые коды
    session.exec(
        delete(TelegramLinkCode).where(
            TelegramLinkCode.user_id == user.id
        )
    )
    # Генерируем новый код
    code = str(uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    link_code = TelegramLinkCode(user_id=user.id, code=code, created_at=datetime.utcnow(), expires_at=expires_at)
    session.add(link_code)
    session.commit()
    session.refresh(link_code)
    return {"success": True, "code": code, "expires_at": expires_at.isoformat()}


    
