from fastapi import Depends, HTTPException, status 
from fastapi.security import OAuth2PasswordBearer
from auth.jwt_handler import verify_access_token 
from services.auth.cookieauth import OAuth2PasswordBearerWithCookie

# Схема OAuth2 для получения токена из заголовка Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/signin")

async def authenticate(token: str=Depends(oauth2_scheme)) -> str:
    """
    Проверяет JWT токен, переданный в заголовке Authorization.
    
    Args:
        token (str): JWT токен из заголовка Authorization
        
    Returns:
        str: Идентификатор пользователя из токена
        
    Raises:
        HTTPException: Если токен отсутствует или недействителен
    """
    if not token:
        raise HTTPException( 
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="Sign in for access"
        )
    decoded_token = verify_access_token(token) 
    return decoded_token["user"]

# Схема OAuth2 для получения токена из cookie
oauth2_scheme_cookie = OAuth2PasswordBearerWithCookie(tokenUrl="/auth/token")

async def authenticate_cookie(token: str=Depends(oauth2_scheme_cookie)) -> str:
    """
    Проверяет JWT токен, переданный через cookie.
    
    Args:
        token (str): JWT токен из cookie
        
    Returns:
        str: Идентификатор пользователя из токена
        
    Raises:
        HTTPException: Если токен отсутствует или недействителен
    """
    if not token:
        raise HTTPException( 
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="Sign in for access"
        )
    token = token.removeprefix('Bearer ')
    decoded_token = verify_access_token(token) 
    return decoded_token["user"]