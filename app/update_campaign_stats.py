#!/usr/bin/env python3

import sys
import os
sys.path.append("/app")

from sqlmodel import Session, select, text
from app.database.simple_engine import simple_engine

def update_campaign_stats():
    """Обновляет статистику для всех существующих кампаний"""
    with Session(simple_engine) as session:
        # Получаем все кампании
        campaigns = session.exec(text("SELECT id, name FROM telegramcampaign ORDER BY created_at DESC")).all()
        
        for campaign_id, campaign_name in campaigns:
            print(f"Обновляем статистику для кампании {campaign_id}: {campaign_name}")
            
            # Получаем статистику сообщений для этой кампании
            stats_query = text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending,
                    COUNT(CASE WHEN status = 'SENT' THEN 1 END) as sent,
                    COUNT(CASE WHEN status = 'DELIVERED' THEN 1 END) as delivered,
                    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
                FROM telegrammessage 
                WHERE campaign_id = :campaign_id
            """)
            
            stats = session.exec(stats_query.bindparams(campaign_id=str(campaign_id))).first()
            
            if stats:
                total, pending, sent, delivered, failed = stats
                print(f"  Статистика: всего={total}, отправлено={sent}, доставлено={delivered}, ошибок={failed}")
                
                # Обновляем статистику в кампании
                update_query = text("""
                    UPDATE telegramcampaign 
                    SET sent_count = :sent, delivered_count = :delivered, failed_count = :failed
                    WHERE id = :campaign_id
                """)
                
                session.exec(update_query.bindparams(
                    sent=sent or 0,
                    delivered=delivered or 0,
                    failed=failed or 0,
                    campaign_id=campaign_id
                ))
        
        session.commit()
        print("Обновление завершено!")

if __name__ == "__main__":
    update_campaign_stats() 