# 🔧 Устранение неполадок

Руководство по решению типичных проблем при работе с Figaro Festival.

## 📋 Содержание

- [🐳 Docker проблемы](#-docker-проблемы)
- [🗄️ База данных](#️-база-данных)
- [🔐 Аутентификация](#-аутентификация)
- [📱 Telegram Bot](#-telegram-bot)
- [🔄 Celery задачи](#-celery-задачи)
- [🌐 Веб-интерфейс](#-веб-интерфейс)
- [📊 Рекомендательная система](#-рекомендательная-система)
- [🧪 Тестирование](#-тестирование)

## 🐳 Docker проблемы

### Проблема: Контейнеры не запускаются

**Симптомы:**
```
Error: Cannot connect to the Docker daemon
```

**Решение:**
```bash
# Проверьте статус Docker
sudo systemctl status docker

# Запустите Docker если не запущен
sudo systemctl start docker

# Проверьте права пользователя
sudo usermod -aG docker $USER
# Перезапустите терминал
```

### Проблема: Порты уже заняты

**Симптомы:**
```
Error: Port 8000 is already in use
```

**Решение:**
```bash
# Найдите процесс, использующий порт
sudo lsof -i :8000

# Остановите процесс
sudo kill -9 <PID>

# Или измените порт в docker-compose.yaml
ports:
  - "8001:8000"  # Внешний порт 8001
```

### Проблема: Недостаточно памяти

**Симптомы:**
```
Error: Container killed due to memory limit
```

**Решение:**
```bash
# Увеличьте лимиты в docker-compose.yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

## 🗄️ База данных

### Проблема: Не удается подключиться к PostgreSQL

**Симптомы:**
```
psycopg2.OperationalError: could not connect to server
```

**Решение:**
```bash
# Проверьте статус контейнера БД
docker compose ps db

# Перезапустите БД
docker compose restart db

# Проверьте логи
docker compose logs db

# Проверьте переменные окружения
docker compose exec app env | grep DATABASE
```

### Проблема: Миграции не применяются

**Симптомы:**
```
Table 'users' already exists
```

**Решение:**
```bash
# Сбросьте БД
docker compose down -v
docker compose up db -d

# Примените миграции заново
docker compose exec app python -m alembic upgrade head
```

### Проблема: Медленные запросы

**Симптомы:**
- Долгая загрузка страниц
- Таймауты API

**Решение:**
```bash
# Проверьте индексы
docker compose exec db psql -U user -d figaro -c "\d+ users"

# Добавьте индексы для часто используемых полей
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_concerts_date ON concerts(date);
```

## 🔐 Аутентификация

### Проблема: JWT токены не работают

**Симптомы:**
```
401 Unauthorized: Invalid token
```

**Решение:**
```bash
# Проверьте SECRET_KEY
docker compose exec app env | grep SECRET_KEY

# Сгенерируйте новый ключ
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Обновите .env файл
SECRET_KEY=your-new-secret-key
```

### Проблема: Пользователи не могут войти

**Симптомы:**
```
Invalid email or password
```

**Решение:**
```bash
# Проверьте хеширование паролей
docker compose exec app python -c "
from app.auth.hash_password import hash_password, verify_password
print(verify_password('password123', hash_password('password123')))
"

# Сбросьте пароль пользователя
docker compose exec app python -c "
from app.database.database import get_session
from app.models.user import User
from app.auth.hash_password import hash_password

session = next(get_session())
user = session.exec(select(User).where(User.email == 'admin@example.com')).first()
user.password = hash_password('newpassword')
session.add(user)
session.commit()
"
```

## 📱 Telegram Bot

### Проблема: Бот не отвечает

**Симптомы:**
- Сообщения не доставляются
- Webhook ошибки

**Решение:**
```bash
# Проверьте токен бота
docker compose exec bot env | grep TELEGRAM_TOKEN

# Проверьте логи бота
docker compose logs bot

# Установите webhook вручную
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhook"}'
```

### Проблема: Webhook не работает

**Симптомы:**
```
404 Not Found при обращении к webhook
```

**Решение:**
```bash
# Проверьте настройки nginx
docker compose exec web nginx -t

# Проверьте SSL сертификаты
docker compose exec web openssl s_client -connect your-domain.com:443

# Настройте правильный URL в .env
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook
```

## 🔄 Celery задачи

### Проблема: Задачи не выполняются

**Симптомы:**
- Задачи остаются в статусе PENDING
- Ошибки в логах worker

**Решение:**
```bash
# Проверьте статус RabbitMQ
docker compose ps rabbitmq

# Перезапустите worker
docker compose restart worker

# Проверьте логи worker
docker compose logs worker

# Проверьте подключение к RabbitMQ
docker compose exec worker celery -A celery_worker inspect ping
```

### Проблема: Задачи выполняются медленно

**Симптомы:**
- Долгое время выполнения задач
- Очереди переполнены

**Решение:**
```bash
# Увеличьте количество worker процессов
docker compose exec worker celery -A celery_worker worker --loglevel=info --concurrency=4

# Мониторинг через Flower
# Откройте http://localhost:5555

# Проверьте нагрузку на RabbitMQ
docker compose exec rabbitmq rabbitmqctl list_queues
```

## 🌐 Веб-интерфейс

### Проблема: Статические файлы не загружаются

**Симптомы:**
- CSS/JS не загружаются
- 404 ошибки для статических файлов

**Решение:**
```bash
# Проверьте настройки nginx
docker compose exec web cat /etc/nginx/nginx.conf

# Проверьте права доступа
docker compose exec app ls -la /app/static/

# Перезапустите nginx
docker compose restart web
```

### Проблема: API возвращает 500 ошибки

**Симптомы:**
```
500 Internal Server Error
```

**Решение:**
```bash
# Проверьте логи приложения
docker compose logs app

# Проверьте подключение к БД
docker compose exec app python -c "
from app.database.database import get_session
session = next(get_session())
print('DB connection OK')
"

# Проверьте переменные окружения
docker compose exec app env | grep -E "(DEBUG|LOG_LEVEL)"
```

## 📊 Рекомендательная система

### Проблема: Рекомендации не генерируются

**Симптомы:**
- Пустые списки рекомендаций
- Ошибки в алгоритме

**Решение:**
```bash
# Проверьте данные в БД
docker compose exec db psql -U user -d figaro -c "SELECT COUNT(*) FROM concerts;"
docker compose exec db psql -U user -d figaro -c "SELECT COUNT(*) FROM routes;"

# Проверьте кэш
docker compose exec app python -c "
from app.services.recommendation import RecommendationService
service = RecommendationService()
print('Cache status:', service.get_cache_status())
"
```

### Проблема: Медленная генерация рекомендаций

**Симптомы:**
- Долгое время ответа API
- Таймауты

**Решение:**
```bash
# Оптимизируйте запросы
docker compose exec app python app/test_route_performance.py

# Включите кэширование
docker compose exec app python -c "
from app.services.recommendation import RecommendationService
service = RecommendationService()
service.enable_caching(True)
"
```

## 🧪 Тестирование

### Проблема: Тесты не проходят

**Симптомы:**
```
pytest: FAILED
```

**Решение:**
```bash
# Запустите тесты с подробным выводом
pytest -v --tb=long

# Проверьте тестовую БД
docker compose exec test_db psql -U test_user -d test_figaro -c "\dt"

# Очистите кэш pytest
pytest --cache-clear
```

### Проблема: Низкое покрытие кода

**Симптомы:**
```
Coverage: 45%
```

**Решение:**
```bash
# Запустите тесты с покрытием
pytest --cov=app --cov-report=html

# Откройте отчет покрытия
open htmlcov/index.html

# Добавьте тесты для недостающих функций
```

## 🔍 Полезные команды

### Мониторинг системы
```bash
# Статус всех сервисов
docker compose ps

# Использование ресурсов
docker stats

# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f app
```

### Отладка
```bash
# Войти в контейнер приложения
docker compose exec app bash

# Проверить переменные окружения
docker compose exec app env

# Запустить Python shell
docker compose exec app python

# Проверить подключения к БД
docker compose exec app python -c "from app.database.database import get_session; print('DB OK')"
```

### Восстановление
```bash
# Полный сброс системы
docker compose down -v
docker compose up -d

# Сброс только данных
docker compose down -v
docker compose up db -d
docker compose exec db psql -U user -d figaro -f /docker-entrypoint-initdb.d/init.sql
```

## 📞 Получение помощи

Если проблема не решается:

1. **Проверьте Issues** на GitHub
2. **Создайте новый Issue** с подробным описанием
3. **Приложите логи** и конфигурацию
4. **Опишите шаги** для воспроизведения

### Полезные ссылки
- [Docker документация](https://docs.docker.com/)
- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Celery документация](https://docs.celeryproject.org/)
- [PostgreSQL документация](https://www.postgresql.org/docs/)

---

💡 **Совет**: Всегда проверяйте логи сервисов перед обращением за помощью! 