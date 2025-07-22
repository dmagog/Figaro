# Архитектура интеграции Telegram-бота с FastAPI, Celery и RabbitMQ

## 📌 Цель

Организовать взаимодействие между FastAPI веб-сервисом и Telegram-ботом через очередь задач, используя:
- **Celery** — для асинхронной постановки и обработки задач
- **RabbitMQ** — как брокер сообщений
- **aiogram** — для общения с Telegram API
- **Docker** — для контейнеризации всех компонентов

---

## 🧱 Общая архитектура

```
Пользователь → FastAPI → Celery → RabbitMQ → Celery Worker → Telegram Bot (aiogram) → Telegram
```

---

## 📁 Структура проекта

```
project/
│
├── app/                   # FastAPI-приложение
│   ├── api.py
│   └── tasks.py           # Импорт и вызов задач Celery
│
├── worker/                # Celery worker
│   ├── celery_worker.py
│   └── tasks.py           # Функции для выполнения (в т.ч. через aiogram)
│
├── bot/                   # aiogram бот
│   ├── bot.py             # Telegram Bot API и логика отправки
│
├── docker-compose.yml
└── .env
```

---


---

## 🐳 Пример Dockerfile для Celery Worker

```dockerfile
FROM python:3.10-slim

WORKDIR /worker

COPY ./worker /worker
COPY ./bot /bot

RUN pip install celery aiogram

CMD ["celery", "-A", "celery_worker", "worker", "--loglevel=info"]
```

---

## 📦 .env файл

```
TELEGRAM_TOKEN=your_actual_token
```

---

## 🧠 Рекомендации

- Оборачивай `send_telegram_message` в retry-логику при ошибках (например, 429 от Telegram).
- Используй `Flower` (`pip install flower`) для мониторинга задач Celery.
- Можно добавить `crontab`/`periodic` задачи для напоминаний.
