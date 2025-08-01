#!/usr/bin/env python3
"""
Скрипт для создания тестовых уведомлений
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import get_session
from app.services.notification_service import NotificationService
from app.models import NotificationType
from datetime import datetime, timedelta

def create_test_notifications():
    """Создает тестовые уведомления"""
    session = next(get_session())
    
    try:
        # Создаем несколько тестовых уведомлений
        notifications = [
            {
                "type": NotificationType.INFO,
                "title": "Новый пользователь зарегистрировался",
                "message": "Пользователь admin@example.com успешно зарегистрировался в системе",
                "entity_type": "user",
                "entity_id": 1
            },
            {
                "type": NotificationType.INFO,
                "title": "Telegram бот активен",
                "message": "Бот успешно обработал 15 сообщений за последний час",
                "entity_type": "telegram",
                "entity_id": None
            },
            {
                "type": NotificationType.WARNING,
                "title": "Высокая активность на сайте",
                "message": "За последние 30 минут зафиксировано 50 посещений",
                "entity_type": "system",
                "entity_id": None
            },
            {
                "type": NotificationType.SUCCESS,
                "title": "Резервное копирование завершено",
                "message": "База данных успешно сохранена в 15:30",
                "entity_type": "system",
                "entity_id": None
            }
        ]
        
        created_count = 0
        for notification_data in notifications:
            notification = NotificationService.create_notification(
                session=session,
                type=notification_data["type"],
                title=notification_data["title"],
                message=notification_data["message"],
                entity_type=notification_data["entity_type"],
                entity_id=notification_data["entity_id"]
            )
            created_count += 1
            print(f"Создано уведомление: {notification.title}")
        
        print(f"\n✅ Создано {created_count} тестовых уведомлений")
        
    except Exception as e:
        print(f"❌ Ошибка создания уведомлений: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_test_notifications() 