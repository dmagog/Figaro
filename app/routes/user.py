from fastapi import APIRouter, HTTPException, status, Depends, Form
from fastapi.security import OAuth2PasswordRequestForm
from database.database import get_session
from models.user import *
from services.crud import user as UserService
from typing import List, Dict
from services.logging.logging import get_logger
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from fastapi.responses import RedirectResponse

logger = get_logger(logger_name=__name__)

user_route = APIRouter()
hash_password = HashPassword()


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
    


    
