"""
Роуты для работы с пользователями
"""
# Временно импортируем все из старого файла для восстановления работоспособности
from .temp_routes import user_route

# Здесь будут импортироваться все подмодули после рефакторинга
# from .auth import auth_router
# from .profile import profile_router
# from .debug import debug_router
# from .telegram import telegram_router

# user_route.include_router(auth_router)
# user_route.include_router(profile_router)
# user_route.include_router(debug_router)
# user_route.include_router(telegram_router) 