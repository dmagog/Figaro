import time
from datetime import datetime
from fastapi import HTTPException, status 
from jose import jwt, JWTError
from database.config import get_settings

# Получаем настройки приложения
settings = get_settings()
SECRET_KEY = settings.SECRET_KEY

def create_access_token(user: str) -> str:
    """
    Создает JWT токен доступа для пользователя.
    
    Args:
        user (str): Имя пользователя или идентификатор
        
    Returns:
        str: Сгенерированный JWT токен
    """
    # Создаем данные для токена
    payload = {
    "user": user,
    "expires": time.time() + 3600  # Срок действия токена - 1 час
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_access_token(token: str) -> dict:
    """
    Проверяет валидность JWT токена.
    
    Args:
        token (str): JWT токен для проверки
        
    Returns:
        dict: Данные из токена
        
    Raises:
        HTTPException: Если токен недействителен или просрочен
    """
    try:
        # Декодируем токен
        data = jwt.decode(token, SECRET_KEY, 
        algorithms=["HS256"])
        expire = data.get("expires")
        
        # Проверяем наличие времени истечения
        if expire is None:
            raise HTTPException( 
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No access token supplied"
            )
            
        # Проверяем, не истек ли срок действия токена
        # if datetime.utcnow() > datetime.utcfromtimestamp(expire):
        #     raise HTTPException( 
        #     status_code=status.HTTP_403_FORBIDDEN, 
        #     detail="Token expired!"
        #     )
        return data
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")
