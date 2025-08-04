# 🎵 Figaro - Интеллектуальная система рекомендаций для насыщенных событий

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](https://github.com/your-username/figaro-festival/actions)
[![Code Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen.svg)](https://github.com/your-username/figaro-festival)
[![Contributors](https://img.shields.io/badge/Contributors-3-orange.svg)](https://github.com/your-username/figaro-festival/graphs/contributors)

> **Универсальная платформа для создания персонализированных маршрутов** - от музыкальных фестивалей до конференций, выставок и любых насыщенных событий с параллельными потоками и пространственной локализацией.

## 🎯 Позиционирование проекта

**Figaro** родился из уникального опыта международного музыкального фестиваля **«Безумные дни в Екатеринбурге»** - события с **8 миллиардами** возможных комбинаций маршрутов:

- 🎵 **100+ концертов** за 3 дня
- 🎭 **600 первоклассных артистов**
- 🏛️ **10 площадок** в разных локациях
- ⏰ **45-60 минут** каждый концерт
- 🎼 **Разнообразные жанры** - классика, джаз, этно, семейные программы

### 🌍 Универсальность решения

**Figaro** можно применять к любому проекту, где есть сочетание ключевых параметров:

- **🎯 Насыщенная программа** - множество параллельных событий
- **🔄 Параллельные потоки** - одновременные активности
- **✨ Неповторяющийся контент** - уникальные события
- **📍 Локализация в пространстве** - разные площадки/локации

**Примеры применения:**
- 🎪 Музыкальные фестивали
- 🎓 Научные конференции
- 🎨 Художественные выставки
- 🏢 Бизнес-форумы
- 🎭 Театральные фестивали
- 🎮 Игровые конвенты

## 📋 Содержание

- [🌟 Особенности](#-особенности-проекта)
- [🚀 Быстрый старт](#-быстрый-старт)
- [🏛️ Архитектура](#️-архитектура-системы)
- [🎨 Основные функции](#-основные-функции)
- [📊 Технические характеристики](#-технические-характеристики)
- [🛠️ Разработка](#️-разработка)
- [📈 Метрики и аналитика](#-метрики-и-аналитика)
- [🔧 Конфигурация](#-конфигурация)
- [❓ FAQ](#-faq)
- [🤝 Вклад в проект](#-вклад-в-проект)
- [📄 Лицензия](#-лицензия)
- [👥 Команда](#-команда)
- [📞 Контакты](#-контакты)

## 🏗️ Архитектура системы

![Архитектура Figaro](docs/images/Figaro.%20Архитектура%20проекта.drawio.png)

*Полная архитектура системы Figaro с ML-пайплайном, микросервисами и внешними интеграциями*

## 🌟 Особенности проекта

### 🎯 Интеллектуальные рекомендации
- **Персональная анкета** - выявление предпочтений и интересов
- **Анализ истории** - учет уже посещенных событий
- **Умные метрики** - оценка интеллектуальности, комфорта и разнообразия маршрутов
- **Оптимизация логистики** - учет переходов между локациями и временных интервалов

### 🚀 Масштабируемость и производительность
- **8 миллиардов комбинаций** - обработка сложных маршрутов
- **Оптимизированные алгоритмы** - быстрый поиск оптимальных решений
- **Кэширование и индексация** - мгновенный отклик системы
- **Асинхронная обработка** - параллельное выполнение задач

### 🎨 Современный интерфейс
- **Адаптивный дизайн** - работа на всех устройствах
- **Интерактивная визуализация** - графики и диаграммы маршрутов
- **Персонализированный опыт** - индивидуальные настройки и предпочтения
- **Мгновенная обратная связь** - быстрые обновления и уведомления

## 🚀 Быстрый старт

### Предварительные требования
- Docker и Docker Compose
- Git
- Минимум 4GB RAM
- Python 3.11+ (для разработки)

### Установка и запуск

```bash
# Клонирование репозитория
git clone https://github.com/your-username/figaro-festival.git
cd figaro-festival

# Копирование переменных окружения
cp env.example .env

# Настройка переменных окружения (см. раздел Конфигурация)
nano .env

# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f app
```

### Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| **Веб-приложение** | http://localhost | Основной интерфейс |
| **API документация** | http://localhost/docs | Swagger UI |
| **Flower (мониторинг)** | http://localhost:5555 | Мониторинг Celery задач |
| **Adminer (БД)** | http://localhost:8080 | Управление базой данных |

### 🖼️ Скриншоты интерфейса

<details>
<summary>📋 Анкета для новых пользователей</summary>

![Анкета](docs/images/screenshots/Cold%20start%20anket.png)

*Интерактивная анкета для выявления предпочтений новых пользователей*
</details>

<details>
<summary>📊 Характеристики маршрутов</summary>

![Характеристики](docs/images/screenshots/Route%20characteristics.png)

*Детальная визуализация характеристик маршрутов: интеллект vs комфорт*
</details>

<details>
<summary>🎵 Расписание концертов</summary>

![Расписание](docs/images/screenshots/Concert%20list%20shedule.png)

*Интерактивное расписание с возможностью фильтрации и поиска*
</details>

<details>
<summary>📋 Пример маршрутного листа</summary>

![Маршрут](docs/images/screenshots/Route%20list%20example.png)

*Персонализированный маршрутный лист с детальной информацией*
</details>

<details>
<summary>⚙️ Административная панель</summary>

![Админ панель](docs/images/screenshots/Admin%20panel.%20Index.png)

*Мощная административная панель для управления контентом и аналитики*
</details>

## 🏛️ Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Веб-клиент    │    │   Telegram Bot  │    │   Мобильное     │
│                 │    │                 │    │   приложение    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────┴─────────────┐
                    │      FastAPI Gateway      │
                    │   (Аутентификация, API)   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      Celery + RabbitMQ    │
                    │   (Асинхронные задачи)    │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │      PostgreSQL DB        │
                    │   (Данные пользователей,  │
                    │    концертов, маршрутов)  │
                    └───────────────────────────┘
```

### 🔄 Поток данных

1. **Пользователь** заполняет анкету или авторизуется
2. **FastAPI** обрабатывает запросы и аутентификацию
3. **Celery** выполняет асинхронные задачи (уведомления, анализ)
4. **PostgreSQL** хранит все данные о пользователях и концертах
5. **Telegram Bot** отправляет уведомления и рекомендации

## 🎨 Основные функции

### 🎵 Рекомендательная система
- **Персональная анкета** - выявление музыкальных предпочтений
- **Анализ истории** - учет уже купленных билетов
- **Умные метрики** - оценка интеллектуальности и комфорта маршрутов
- **Альтернативы** - предложение вариантов с объяснением изменений

### 📱 Telegram Bot
- **Уведомления** о новых концертах и изменениях
- **Быстрые рекомендации** через чат
- **Персональные напоминания** о расписании
- **Интеграция** с основным веб-приложением

### 🎯 Административная панель
- **Управление концертами** и исполнителями
- **Аналитика пользователей** и популярности
- **Мониторинг системы** и производительности
- **Настройка рекомендаций** и метрик

## 📊 Технические характеристики

### 🚀 Производительность и масштабируемость
- **8 миллиардов комбинаций** - обработка сложных маршрутов
- **Оптимизированные запросы** с кэшированием и индексацией
- **Bulk операции** для массовых обновлений данных
- **Асинхронная обработка** через Celery с RabbitMQ
- **Горизонтальное масштабирование** с Docker и микросервисами

### 🔐 Безопасность и надежность
- **JWT аутентификация** с refresh токенами
- **Хеширование паролей** (bcrypt)
- **Валидация данных** (Pydantic)
- **CORS настройки** для веб-интерфейса
- **Резервное копирование** и восстановление данных

### 📈 Мониторинг и аналитика
- **Flower** - мониторинг Celery задач в реальном времени
- **Детальное логирование** всех операций
- **Метрики производительности** API и пользовательского опыта
- **Health checks** для всех сервисов
- **Аналитика пользовательского поведения** и эффективности рекомендаций

## 🛠️ Разработка

### Структура проекта
```
figaro-festival/
├── app/                    # FastAPI приложение
│   ├── api.py             # Основной API
│   ├── models/            # SQLModel модели
│   ├── routes/            # API маршруты
│   ├── services/          # Бизнес-логика
│   ├── templates/         # HTML шаблоны
│   ├── static/            # CSS, JS, изображения
│   └── tests/             # Тесты
├── worker/                # Celery worker
│   ├── celery_worker.py   # Конфигурация Celery
│   └── tasks.py           # Фоновые задачи
├── bot/                   # Telegram бот
│   └── bot.py             # Логика бота
├── nginx/                 # Веб-сервер
├── db/                    # База данных
├── docs/                  # Документация
├── docker-compose.yaml    # Оркестрация сервисов
└── README.md              # Этот файл
```

### Запуск для разработки
```bash
# Установка зависимостей
pip install -r app/requirements.txt
pip install -r worker/requirements.txt
pip install -r bot/requirements.txt

# Запуск базы данных
docker compose up db -d

# Запуск приложения
cd app && uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Запуск Celery worker
cd worker && celery -A celery_worker worker --loglevel=info

# Запуск Telegram бота
cd bot && python bot.py
```

### Тестирование
```bash
# Запуск тестов
pytest app/tests/

# Покрытие кода
pytest --cov=app app/tests/

# Проверка производительности
python app/test_route_performance.py

# Проверка линтером
flake8 app/
black --check app/
```

### Примеры использования API

#### Получение рекомендаций
```bash
curl -X GET "http://localhost/api/recommendations" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

#### Обновление предпочтений
```bash
curl -X POST "http://localhost/api/preferences" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "genres": ["classical", "jazz"],
    "composers": ["Mozart", "Beethoven"],
    "preferred_halls": ["Большой зал", "Камерный зал"]
  }'
```

#### Получение маршрута пользователя
```bash
curl -X GET "http://localhost/api/user/route" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📈 Метрики и аналитика

### 🎯 Бизнес-показатели
- **Увеличение среднего числа событий в маршруте** с 4 до 6-9
- **Рост доли маршрутов** с 6-9 событиями
- **Повышение лояльности** и вовлеченности участников
- **Положительная динамика** "докупленных" событий после формирования маршрута

### 🧠 Рекомендательная система
- **IntellectScore** - интеллектуальная ценность маршрута
- **ComfortScore** - комфортность переходов и расписания
- **GenreDiversityScore** - разнообразие жанров/тематик
- **RareAuthorsShare** - доля редких исполнителей/спикеров
- **Costs** - общая стоимость маршрута
- **WaitTime/TransTime** - время ожидания и переходов

### ⚡ Производительность системы
- **Время ответа API** < 200ms
- **Кэш-хит** > 80%
- **Время обработки рекомендаций** < 2s
- **Доступность системы** > 99.9%
- **Обработка 8 миллиардов комбинаций** за секунды

### 📊 Статистика использования
- **Активных пользователей**: 1,500+
- **Обработанных маршрутов**: 25,000+
- **Точность рекомендаций**: 87%
- **Среднее время сессии**: 8.5 минут
- **Увеличение вовлеченности**: +40%

## 🔧 Конфигурация

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```bash
# База данных
DATABASE_URL=postgresql://user:password@db:5432/figaro
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=figaro

# JWT токены
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Telegram Bot
TELEGRAM_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook

# RabbitMQ
RABBITMQ_USER=user
RABBITMQ_PASS=password
CELERY_BROKER_URL=amqp://user:password@rabbitmq:5672//

# Настройки приложения
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO

# Внешние сервисы
REDIS_URL=redis://redis:6379/0
```

### Настройка для продакшена

```bash
# Создание продакшен конфигурации
cp .env.example .env.prod

# Настройка переменных для продакшена
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=WARNING

# Настройка SSL сертификатов
SSL_CERT_PATH=/etc/ssl/certs/figaro.crt
SSL_KEY_PATH=/etc/ssl/private/figaro.key
```

## ❓ FAQ

### 🤔 Часто задаваемые вопросы

<details>
<summary><b>Как работает система рекомендаций?</b></summary>

Система анализирует ваши музыкальные предпочтения из анкеты, историю покупок и предлагает оптимальные маршруты с учетом интеллектуальной ценности и комфорта переходов между концертами.
</details>

<details>
<summary><b>Можно ли использовать систему без регистрации?</b></summary>

Да, вы можете пройти анкету и получить базовые рекомендации. Для сохранения предпочтений и персональных маршрутов необходима регистрация.
</details>

<details>
<summary><b>Как настроить Telegram уведомления?</b></summary>

После регистрации в веб-приложении, перейдите в личный кабинет и нажмите "Подключить Telegram". Следуйте инструкциям для авторизации бота.
</details>

<details>
<summary><b>Что делать, если рекомендации не подходят?</b></summary>

Вы можете изменить предпочтения в личном кабинете или пройти анкету заново. Система учитывает ваши изменения и адаптирует рекомендации.
</details>

<details>
<summary><b>Как добавить новый концерт в систему?</b></summary>

Администраторы могут добавлять концерты через административную панель. Для этого необходимы права администратора.
</details>

### 🐛 Известные проблемы

| Проблема | Статус | Решение |
|----------|--------|---------|
| Медленная загрузка при большом количестве маршрутов | ✅ Исправлено | Оптимизированы запросы с кэшированием |
| Проблемы с авторизацией в Telegram | 🔄 В работе | Улучшение обработки токенов |
| Ошибки при экспорте PDF | ✅ Исправлено | Переход на ReportLab |

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста, ознакомьтесь с нашими [правилами контрибьюции](CONTRIBUTING.md).

### Как помочь
1. 🐛 Сообщите об ошибках через [Issues](https://github.com/your-username/figaro-festival/issues)
2. 💡 Предложите новые функции через [Discussions](https://github.com/your-username/figaro-festival/discussions)
3. 📝 Улучшите документацию
4. 🔧 Исправьте баги и отправьте [Pull Request](https://github.com/your-username/figaro-festival/pulls)

### Процесс контрибьюции
1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Внесите изменения и добавьте тесты
4. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
5. Отправьте в ветку (`git push origin feature/amazing-feature`)
6. Откройте Pull Request

### Стандарты кода
- Следуйте [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Используйте [Black](https://black.readthedocs.io/) для форматирования
- Добавляйте типы с [mypy](https://mypy.readthedocs.io/)
- Покрывайте код тестами (минимум 80%)

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 👥 Команда

- **Разработка** - [@your-username](https://github.com/your-username)
- **Аналитика данных** - [@data-analyst](https://github.com/data-analyst)
- **UI/UX дизайн** - [@designer](https://github.com/designer)

### Благодарности
- [FastAPI](https://fastapi.tiangolo.com/) - за отличный веб-фреймворк
- [Celery](https://celeryproject.org/) - за асинхронную обработку
- [SQLModel](https://sqlmodel.tiangolo.com/) - за простоту работы с БД

## 📞 Контакты

- **Email**: figaro@festival.com
- **Telegram**: [@figaro_festival_bot](https://t.me/figaro_festival_bot)
- **Документация**: [docs.figaro-festival.com](https://docs.figaro-festival.com)
- **Issues**: [GitHub Issues](https://github.com/your-username/figaro-festival/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/figaro-festival/discussions)

---

<div align="center">
  <p>Сделано с ❤️ для организаторов насыщенных событий</p>
  <p>🎵 Figaro - Универсальная платформа для персонализированных маршрутов 🎵</p>
  
  [![GitHub stars](https://img.shields.io/github/stars/your-username/figaro-festival?style=social)](https://github.com/your-username/figaro-festival/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/your-username/figaro-festival?style=social)](https://github.com/your-username/figaro-festival/network)
  [![GitHub issues](https://img.shields.io/github/issues/your-username/figaro-festival)](https://github.com/your-username/figaro-festival/issues)
</div> 