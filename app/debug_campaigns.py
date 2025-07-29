#!/usr/bin/env python3

import sys
import os
sys.path.append("/app")

from sqlmodel import Session, select, text
from app.database.simple_engine import simple_engine

def debug_campaigns():
    """Отладочная информация о кампаниях"""
    with Session(simple_engine) as session:
        # Получаем все кампании
        campaigns = session.exec(text("SELECT id, name, target_users_count, sent_count, delivered_count, failed_count, created_at FROM telegramcampaign ORDER BY created_at DESC LIMIT 5")).all()
        
        print("=== КАМПАНИИ В БАЗЕ ДАННЫХ ===")
        for campaign in campaigns:
            print(f"ID: {campaign[0]}")
            print(f"Название: {campaign[1]}")
            print(f"Целевых: {campaign[2]}")
            print(f"Отправлено: {campaign[3]}")
            print(f"Доставлено: {campaign[4]}")
            print(f"Ошибок: {campaign[5]}")
            print(f"Создана: {campaign[6]}")
            print("---")
        
        # Проверяем, что передается в шаблон
        from app.models.telegram_stats import TelegramCampaign
        recent_campaigns = session.exec(
            select(TelegramCampaign).order_by(TelegramCampaign.created_at.desc()).limit(5)
        ).all()
        
        print("=== КАМПАНИИ ЧЕРЕЗ SQLMODEL ===")
        for campaign in recent_campaigns:
            print(f"ID: {campaign.id}")
            print(f"Название: {campaign.name}")
            print(f"Целевых: {campaign.target_users_count}")
            print(f"Отправлено: {campaign.sent_count}")
            print(f"Доставлено: {campaign.delivered_count}")
            print(f"Ошибок: {campaign.failed_count}")
            print(f"Создана: {campaign.created_at}")
            print("---")

if __name__ == "__main__":
    debug_campaigns() 