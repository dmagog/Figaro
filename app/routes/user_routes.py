from fastapi import APIRouter, Depends, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from database.database import get_session
from models.user import User, UserCreate, TelegramLinkCode
from services.crud import user as UserService
from services.crud import purchase as PurchaseService
from typing import List, Dict
from services.logging.logging import get_logger
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from auth.authenticate import authenticate_cookie
from database.config import get_settings
from uuid import uuid4
from datetime import datetime, timedelta
from sqlmodel import select
from fastapi.security import OAuth2PasswordRequestForm
from app.services.user_service import (
    profile_page_logic,
    set_external_id_logic,
    debug_user_external_id_logic,
    set_user_external_id_logic,
    debug_user_purchases_logic,
    generate_telegram_link_code_logic
)

user_route = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()
logger = get_logger(logger_name=__name__)

# Здесь будут все функции с декораторами @user_route.get, @user_route.post, ...
# Например:
# @user_route.get("/profile", response_class=HTMLResponse)
# async def profile_page(...):
#     ...
# Остальные функции будут импортироваться из services.user_service 

@user_route.post('/signup')
async def signup(user: UserCreate, session=Depends(get_session)) -> dict:
    try:
        user_exist = UserService.get_user_by_email(user.email, session)
        if user_exist:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with email provided exists already.")
        new_user = UserService.create_user(
            session=session,
            email=user.email,
            password=user.password,
            name=user.name,
            role=user.role
        )
        return {"message": "User created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )

@user_route.post('/signin')
async def signin(form_data: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)) -> Dict[str, str]:
    user_exist = UserService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    if HashPassword.verify_hash(form_data.password, user_exist.hashed_password):
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
async def profile_page(request: Request, session=Depends(get_session)):
    return await profile_page_logic(request, session)

@user_route.post("/profile/set_external_id")
async def set_profile_external_id(request: Request, session=Depends(get_session)):
    return await set_external_id_logic(request, session)

@user_route.get("/debug/user/{email}/external_id")
async def debug_user_external_id(email: str, session=Depends(get_session)):
    return await debug_user_external_id_logic(email, session)

@user_route.post("/debug/user/{email}/set_external_id/{external_id}")
async def set_user_external_id(email: str, external_id: str, session=Depends(get_session)):
    return await set_user_external_id_logic(email, external_id, session)

@user_route.get("/debug/purchases/{external_id}")
async def debug_user_purchases(external_id: str, session=Depends(get_session)):
    return await debug_user_purchases_logic(external_id, session)

@user_route.post("/telegram/link-code")
async def generate_telegram_link_code(request: Request, session=Depends(get_session)):
    return await generate_telegram_link_code_logic(request, session) 