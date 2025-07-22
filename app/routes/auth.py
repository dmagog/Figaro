from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from auth.authenticate import authenticate_cookie, authenticate
from auth.hash_password import HashPassword
from auth.jwt_handler import create_access_token
from database.database import get_session
from services.auth.loginform import LoginForm, RegisterForm
from services.crud import user as UsersService
from database.config import get_settings
from typing import Dict

# Получаем настройки приложения
settings = get_settings()
# Создаем экземпляр роутера
auth_route = APIRouter()
# Создаем экземпляр для хеширования паролей
hash_password = HashPassword()
# Инициализируем шаблонизатор Jinja2
templates = Jinja2Templates(directory="templates")

@auth_route.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm=Depends(), session=Depends(get_session)) -> dict[str, str]:
    """
    Создает access token для аутентифицированного пользователя.

    Args:
        response (Response): Объект HTTP-ответа для установки cookie
        form_data (OAuth2PasswordRequestForm): Данные формы с email и паролем
        session (Session): Сессия базы данных

    Returns:
        dict[str, str]: Словарь с токеном и типом токена

    Raises:
        HTTPException: 404 если пользователь не найден
        HTTPException: 401 если неверные учетные данные
    """    
    # Проверяем существование пользователя по email
    user_exist = UsersService.get_user_by_email(form_data.username, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    # Проверяем правильность пароля
    if hash_password.verify_hash(form_data.password, user_exist.hashed_password):
        # Создаем JWT токен
        access_token = create_access_token(user_exist.email)
        # Устанавливаем токен в cookie
        response.set_cookie(
            key=settings.COOKIE_NAME, 
            value=f"Bearer {access_token}", 
            httponly=True
        )
        
        # Возвращаем токен в ответе
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

async def authenticate_user(email: str, password: str, session) -> dict[str, str]:
    """
    Аутентифицирует пользователя и создает токен.
    
    Args:
        email: Email пользователя
        password: Пароль пользователя
        session: Сессия базы данных
        
    Returns:
        dict: Словарь с токеном и типом токена
        
    Raises:
        HTTPException: Если аутентификация не удалась
    """
    # Проверяем существование пользователя по email
    user_exist = UsersService.get_user_by_email(email, session)
    if user_exist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User does not exist")
    
    # Проверяем правильность пароля
    if hash_password.verify_hash(password, user_exist.hashed_password):
        # Создаем JWT токен
        access_token = create_access_token(user_exist.email)
        return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid details passed."
    )

@auth_route.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    """
    Отображает страницу входа.

    Args:
        request (Request): Объект HTTP-запроса

    Returns:
        TemplateResponse: HTML-страница с формой входа
    """
    # Передаем объект запроса в шаблон
    context = {
        "request": request,
    }
    return templates.TemplateResponse("login.html", context)

    
@auth_route.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, session=Depends(get_session)):
    """
    Обрабатывает отправку формы входа.

    Args:
        request (Request): Объект HTTP-запроса
        session (Session): Сессия базы данных

    Returns:
        Response: Перенаправление на главную страницу при успехе
        или HTML-страница с ошибками при неудаче
    """
    # Создаем и валидируем форму входа
    form = LoginForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            # Аутентифицируем пользователя
            token_data = await authenticate_user(form.username, form.password, session)
            
            # При успешной аутентификации перенаправляем на главную
            response = RedirectResponse("/", status.HTTP_302_FOUND)
            response.set_cookie(
                key=settings.COOKIE_NAME, 
                value=f"Bearer {token_data[settings.COOKIE_NAME]}", 
                httponly=True
            )
            form.__dict__.update(msg="Login Successful!")
            print("[green]Login successful!!!!")
            return response
        except HTTPException:
            # При ошибке аутентификации показываем сообщение об ошибке
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Incorrect Email or Password")
            return templates.TemplateResponse("login.html", form.__dict__)
    return templates.TemplateResponse("login.html", form.__dict__)

@auth_route.get("/logout", response_class=HTMLResponse)
async def logout():
    """
    Выполняет выход пользователя из системы.

    Returns:
        RedirectResponse: Перенаправление на главную страницу
        с удалением cookie авторизации
    """
    # Создаем редирект и удаляем cookie с токеном
    response = RedirectResponse(url="/")
    response.delete_cookie(settings.COOKIE_NAME)
    return response



@auth_route.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    """
    Отображает страницу регистрации.

    Args:
        request (Request): Объект HTTP-запроса

    Returns:
        TemplateResponse: HTML-страница с формой регистрации
    """
    # Передаем объект запроса в шаблон
    context = {
        "request": request,
    }
    return templates.TemplateResponse("register.html", context)




@auth_route.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, session=Depends(get_session)):
    """
    Обрабатывает отправку формы регистрации.

    Args:
        request (Request): Объект HTTP-запроса
        session (Session): Сессия базы данных

    Returns:
        Response: Перенаправление на главную страницу при успехе
        или HTML-страница с ошибками при неудаче
    """
    # Создаем и валидируем форму регистрации
    form = RegisterForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            # Проверяем, не существует ли уже пользователь с таким email
            existing_user = UsersService.get_user_by_email(form.email, session)
            if existing_user:
                form.__dict__.update(msg="")
                form.__dict__.get("errors").append("User with this email already exists")
                return templates.TemplateResponse("register.html", form.__dict__)
            
            # Создаем нового пользователя
            user = UsersService.create_user(
                session=session,
                email=form.email,
                password=form.password,
                name=form.username
            )
            
            # Аутентифицируем нового пользователя
            token_data = await authenticate_user(form.email, form.password, session)
            
            # При успешной регистрации перенаправляем на главную
            response = RedirectResponse("/", status.HTTP_302_FOUND)
            response.set_cookie(
                key=settings.COOKIE_NAME, 
                value=f"Bearer {token_data[settings.COOKIE_NAME]}", 
                httponly=True
            )
            form.__dict__.update(msg="Registration Successful!")
            print("[green]Registration successful!")
            return response
        except HTTPException:
            # При ошибке аутентификации показываем сообщение об ошибке
            form.__dict__.update(msg="")
            form.__dict__.get("errors").append("Registration failed")
            return templates.TemplateResponse("register.html", form.__dict__)
    return templates.TemplateResponse("register.html", form.__dict__)