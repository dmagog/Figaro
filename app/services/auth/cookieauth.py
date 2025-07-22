# services/auth/cookieauth.py
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """
    Расширение OAuth2PasswordBearer для работы с токенами в cookie.
    """
    
    def __init__(self, tokenUrl: str):
        super().__init__(tokenUrl=tokenUrl)
    
    async def __call__(self, request: Request) -> Optional[str]:
        """
        Извлекает токен из cookie запроса.
        
        Args:
            request: FastAPI Request объект
            
        Returns:
            Optional[str]: Токен из cookie или None
        """
        from database.config import get_settings
        settings = get_settings()
        
        token = request.cookies.get(settings.COOKIE_NAME)
        if token:
            return token
        return None 