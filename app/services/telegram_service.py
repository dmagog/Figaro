import json
import re
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select
from models import User, MessageTemplate, TelegramMessage, TelegramCampaign, MessageStatus, Purchase
from worker.tasks import send_telegram_message
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    """Сервис для работы с Telegram рассылками"""
    
    # Предустановленные шаблоны
    DEFAULT_TEMPLATES = [
        {
            "name": "Приветствие",
            "content": "Привет, {name}! 👋\n\nДобро пожаловать в мир фестиваля 'Безумные дни'! 🎵\n\nМы рады видеть вас в числе наших гостей.",
            "variables": '{"name": "Имя пользователя"}'
        },
        {
            "name": "Напоминание о концерте",
            "content": "Напоминание о концерте!\n\n{concert_name}\nДата: {concert_date}\nЗал: {hall_name}\n\nНе забудьте о билетах!",
            "variables": '{"concert_name": "Название концерта", "concert_date": "Дата концерта", "hall_name": "Название зала"}'
        },
        {
            "name": "Специальное предложение",
            "content": "🎉 Специальное предложение для вас, {name}!\n\n{offer_text}\n\nУспейте воспользоваться до {expiry_date}!",
            "variables": '{"name": "Имя пользователя", "offer_text": "Текст предложения", "expiry_date": "Дата окончания"}'
        },
        {
            "name": "Статистика покупок",
            "content": "📊 Ваша статистика покупок:\n\n🎫 Всего билетов: {tickets_count}\n💰 Общая сумма: {total_spent} ₽\n🎵 Посещено концертов: {concerts_count}\n\nСпасибо за поддержку фестиваля!",
            "variables": '{"tickets_count": "Количество билетов", "total_spent": "Общая сумма", "concerts_count": "Количество концертов"}'
        }
    ]
    
    @staticmethod
    def get_user_data(user: User, session: Session) -> Dict[str, Any]:
        """Получает данные пользователя для персонализации"""
        data = {
            "id": user.id,
            "name": user.name or user.email.split('@')[0] if user.email else "Пользователь",
            "email": user.email,
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "created_at": user.created_at,
            "tickets_count": 0,
            "total_spent": 0,
            "concerts_count": 0,
            "last_purchase": None
        }
        
        # Получаем статистику покупок
        if user.external_id:
            purchases = session.exec(
                select(Purchase).where(Purchase.user_external_id == str(user.external_id))
            ).all()
            
            if purchases:
                data["tickets_count"] = len(purchases)
                data["total_spent"] = sum(p.price or 0 for p in purchases)
                data["concerts_count"] = len(set(p.concert_id for p in purchases))
                data["last_purchase"] = max(p.purchased_at for p in purchases if p.purchased_at)
        
        return data
    
    @staticmethod
    def personalize_message(template: str, user_data: Dict[str, Any]) -> str:
        """Персонализирует сообщение, подставляя переменные"""
        try:
            # Заменяем переменные в шаблоне
            personalized = template
            
            # Основные переменные
            replacements = {
                "{name}": user_data.get("name", "Пользователь"),
                "{email}": user_data.get("email", ""),
                "{telegram_username}": user_data.get("telegram_username", ""),
                "{tickets_count}": str(user_data.get("tickets_count", 0)),
                "{total_spent}": str(user_data.get("total_spent", 0)),
                "{concerts_count}": str(user_data.get("concerts_count", 0)),
                "{user_id}": str(user_data.get("id", "")),
                # Переменные для концертов
                "{concert_name}": user_data.get("concert_name", "Концерт"),
                "{concert_date}": user_data.get("concert_date", "Дата не указана"),
                "{hall_name}": user_data.get("hall_name", "Зал не указан"),
                # Переменные для предложений
                "{offer_text}": user_data.get("offer_text", "Специальное предложение"),
                "{expiry_date}": user_data.get("expiry_date", "Дата не указана"),
            }
            
            for placeholder, value in replacements.items():
                personalized = personalized.replace(placeholder, value)
            
            # Форматируем даты
            if user_data.get("last_purchase"):
                last_purchase = user_data["last_purchase"]
                if isinstance(last_purchase, str):
                    last_purchase = datetime.fromisoformat(last_purchase.replace('Z', '+00:00'))
                personalized = personalized.replace(
                    "{last_purchase}", 
                    last_purchase.strftime("%d.%m.%Y") if last_purchase else "Нет покупок"
                )
            
            return personalized
            
        except Exception as e:
            logger.error(f"Ошибка персонализации сообщения: {e}")
            return template
    
    @staticmethod
    def get_templates(session: Session) -> List[MessageTemplate]:
        """Получает все активные шаблоны"""
        return session.exec(select(MessageTemplate).where(MessageTemplate.is_active == True)).all()
    
    @staticmethod
    def create_template(session: Session, name: str, content: str, variables: str = "") -> MessageTemplate:
        """Создает новый шаблон"""
        template = MessageTemplate(
            name=name,
            content=content,
            variables=variables
        )
        session.add(template)
        session.commit()
        session.refresh(template)
        return template
    
    @staticmethod
    def initialize_default_templates(session: Session):
        """Инициализирует шаблоны по умолчанию"""
        existing_templates = session.exec(select(MessageTemplate)).all()
        if not existing_templates:
            for template_data in TelegramService.DEFAULT_TEMPLATES:
                TelegramService.create_template(
                    session,
                    template_data["name"],
                    template_data["content"],
                    template_data["variables"]
                )
            logger.info("Созданы шаблоны по умолчанию")
    
    @staticmethod
    def send_campaign(
        session: Session,
        users: List[User],
        message_text: str,
        campaign_name: str = None,
        template_id: Optional[int] = None,
        file_path: Optional[str] = None,
        file_type: Optional[str] = None,
        parse_mode: str = None
    ) -> str:
        """Отправляет кампанию сообщений через Celery"""
        
        campaign_id = str(uuid.uuid4())
        
        # Создаем запись о кампании
        campaign = TelegramCampaign(
            name=campaign_name or f"Кампания {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            template_id=template_id,
            target_users_count=len(users),
            sent_at=datetime.utcnow()
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        
        # Создаем записи о сообщениях и ставим задачи в очередь
        for user in users:
            if not user.telegram_id:
                continue
                
            # Персонализируем сообщение
            user_data = TelegramService.get_user_data(user, session)
            personalized_message = TelegramService.personalize_message(message_text, user_data)
            
            # Создаем запись о сообщении
            message_record = TelegramMessage(
                telegram_id=user.telegram_id,
                user_id=user.id,
                message_text=personalized_message,
                file_path=file_path,
                file_type=file_type,
                parse_mode=parse_mode,
                status=MessageStatus.PENDING,
                campaign_id=campaign_id
            )
            session.add(message_record)
            
            # Ставим задачу в очередь Celery
            send_telegram_message.delay(
                telegram_id=user.telegram_id,
                text=personalized_message,
                file_path=file_path,
                file_type=file_type,
                parse_mode=parse_mode,
                message_id=message_record.id
            )
        
        session.commit()
        return campaign_id
    
    @staticmethod
    def get_campaign_stats(session: Session, campaign_id: str) -> Dict[str, Any]:
        """Получает статистику кампании"""
        messages = session.exec(
            select(TelegramMessage).where(TelegramMessage.campaign_id == campaign_id)
        ).all()
        
        stats = {
            "total": len(messages),
            "pending": len([m for m in messages if m.status == MessageStatus.PENDING]),
            "sent": len([m for m in messages if m.status == MessageStatus.SENT]),
            "delivered": len([m for m in messages if m.status == MessageStatus.DELIVERED]),
            "failed": len([m for m in messages if m.status == MessageStatus.FAILED])
        }
        
        return stats
    
    @staticmethod
    def get_user_categories(session: Session) -> Dict[str, List[User]]:
        """Группирует пользователей по категориям"""
        users_with_telegram = session.exec(
            select(User).where(User.telegram_id.is_not(None))
        ).all()
        
        categories = {
            "all": users_with_telegram,
            "with_purchases": [],
            "without_purchases": [],
            "new_users": [],
            "active_users": []
        }
        
        for user in users_with_telegram:
            user_data = TelegramService.get_user_data(user, session)
            
            # Пользователи с покупками
            if user_data["tickets_count"] > 0:
                categories["with_purchases"].append(user)
            else:
                categories["without_purchases"].append(user)
            
            # Новые пользователи (зарегистрированы в последние 30 дней)
            if user.created_at:
                days_since_registration = (datetime.utcnow() - user.created_at).days
                if days_since_registration <= 30:
                    categories["new_users"].append(user)
            
            # Активные пользователи (покупали в последние 90 дней)
            if user_data["last_purchase"]:
                days_since_purchase = (datetime.utcnow() - user_data["last_purchase"]).days
                if days_since_purchase <= 90:
                    categories["active_users"].append(user)
        
        return categories 