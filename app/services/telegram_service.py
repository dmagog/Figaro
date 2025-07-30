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
        },
        {
            "name": "Ваш маршрут концертов",
            "content": "🎵 **Ваш персональный маршрут фестиваля, {name}!**\n\n📊 **Статистика маршрута:**\n🎫 Концертов: **{route_concerts_count}**\n📅 Дней фестиваля: **{route_days}**\n🏛️ Уникальных залов: **{route_halls}**\n🎭 Музыкальных жанров: **{route_genres}**\n⏱️ Общее время концертов: **{route_show_time} мин**\n\n🎼 **Ваши концерты:**\n\n{route_concerts_list}\n\nУдачного фестиваля! 🎉",
            "variables": '{"name": "Имя пользователя", "route_concerts_count": "Количество концертов в маршруте", "route_days": "Количество дней", "route_halls": "Количество залов", "route_genres": "Количество жанров", "route_show_time": "Время концертов (мин)", "route_trans_time": "Время переходов (мин)", "route_wait_time": "Время ожидания (мин)", "route_comfort_score": "Оценка комфорта", "route_intellect_score": "Оценка интеллекта", "route_concerts_list": "Список концертов"}'
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
            "last_purchase": None,
            "route_concerts": [],
            "route_summary": {}
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
            
            # Получаем маршрут пользователя через ту же логику, что и на странице профиля
            try:
                # Используем ту же логику, что и в user.py
                from app.services.crud.purchase import get_user_unique_concerts_with_details
                
                # Получаем уникальные концерты пользователя (как в user.py)
                purchases = get_user_unique_concerts_with_details(session, str(user.external_id))
                
                if purchases:
                    # Преобразуем данные для совместимости с get_user_route_sheet (как в user.py)
                    concerts_for_template = []
                    for purchase in purchases:
                        try:
                            # Создаем копию данных концерта
                            concert_copy = purchase.copy()
                            
                            # Добавляем информацию о количестве билетов
                            concert_copy['tickets_count'] = purchase['concert'].get('purchase_count', 1)
                            concert_copy['total_spent'] = purchase['concert'].get('purchase_count', 1) * (purchase['concert'].get('price', 0) or 0)
                            
                            # Обрабатываем concert datetime
                            if isinstance(purchase['concert']['datetime'], str):
                                from datetime import datetime
                                concert_copy['concert']['datetime'] = datetime.fromisoformat(purchase['concert']['datetime'])
                            else:
                                concert_copy['concert']['datetime'] = purchase['concert']['datetime']
                            
                            concerts_for_template.append(concert_copy)
                            
                        except Exception as e:
                            print(f"Ошибка при обработке концерта: {e}")
                            continue
                    
                    # Сортируем концерты по дате (как в user.py)
                    concerts_for_template.sort(key=lambda x: x['concert']['datetime'] if x['concert']['datetime'] else datetime.min)
                    
                    # Формируем данные для шаблона
                    route_concerts = []
                    
                    # Получаем концерты из обработанных данных
                    for concert_data in concerts_for_template:
                        concert = concert_data['concert']
                        route_concerts.append({
                            "id": concert['id'],
                            "name": concert['name'] or "Название не указано",
                            "date": concert['datetime'].strftime("%d.%m.%Y") if concert['datetime'] else "Дата не указана",
                            "time": concert['datetime'].strftime("%H:%M") if concert['datetime'] else "Время не указано",
                            "hall": concert['hall']['name'] if concert['hall'] else "Зал не указан",
                            "genre": concert['genre'] or "Жанр не указан",
                            "duration": str(concert['duration']) if concert['duration'] else "Длительность не указана"
                        })
                    
                    # Формируем сводку маршрута
                    total_days = len(set(c['concert']['datetime'].date() for c in concerts_for_template if c['concert']['datetime']))
                    total_halls = len(set(c['concert']['hall']['id'] for c in concerts_for_template if c['concert']['hall']))
                    total_genres = len(set(c['concert']['genre'] for c in concerts_for_template if c['concert']['genre']))
                    
                    # Рассчитываем общее время концертов
                    total_show_time = 0
                    for concert_data in concerts_for_template:
                        duration = concert_data['concert']['duration']
                        if duration:
                            if isinstance(duration, str) and ':' in duration:
                                parts = duration.split(':')
                                if len(parts) >= 2:
                                    hours = int(parts[0])
                                    minutes = int(parts[1])
                                    total_show_time += hours * 60 + minutes
                            elif isinstance(duration, (int, float)):
                                total_show_time += duration
                    
                    route_summary = {
                        "total_concerts": len(route_concerts),
                        "total_days": total_days,
                        "total_halls": total_halls,
                        "total_genres": total_genres,
                        "show_time": total_show_time,
                        "trans_time": 0,  # Будем рассчитывать позже
                        "wait_time": 0,   # Будем рассчитывать позже
                        "comfort_score": 0,
                        "intellect_score": 0
                    }
                    
                    data["route_concerts"] = route_concerts
                    data["route_summary"] = route_summary
                        
            except Exception as e:
                print(f"Ошибка при получении данных маршрута: {e}")
        
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
                "{concert_id}": str(user_data.get("concert_id", "")),
                "{concert_date}": user_data.get("concert_date", "Дата не указана"),
                "{hall_name}": user_data.get("hall_name", "Зал не указан"),
                # Переменные для предложений
                "{offer_text}": user_data.get("offer_text", "Специальное предложение"),
                "{expiry_date}": user_data.get("expiry_date", "Дата не указана"),
                # Переменные для маршрута
                "{route_concerts_count}": str(user_data.get("route_summary", {}).get("total_concerts", 0)),
                "{route_days}": str(user_data.get("route_summary", {}).get("total_days", 0)),
                "{route_halls}": str(user_data.get("route_summary", {}).get("total_halls", 0)),
                "{route_show_time}": str(user_data.get("route_summary", {}).get("show_time", 0)),
                "{route_trans_time}": str(user_data.get("route_summary", {}).get("trans_time", 0)),
                "{route_wait_time}": str(user_data.get("route_summary", {}).get("wait_time", 0)),
                "{route_comfort_score}": str(user_data.get("route_summary", {}).get("comfort_score", 0)),
                "{route_intellect_score}": str(user_data.get("route_summary", {}).get("intellect_score", 0)),
                "{route_genres}": str(user_data.get("route_summary", {}).get("total_genres", 0)),
            }
            
            for placeholder, value in replacements.items():
                personalized = personalized.replace(placeholder, value)
            
            # Специальная обработка для списка концертов маршрута
            if "{route_concerts_list}" in personalized:
                route_concerts = user_data.get("route_concerts", [])
                if route_concerts:
                    # Группируем концерты по дням
                    concerts_by_day = {}
                    for concert in route_concerts:
                        date = concert['date']
                        if date not in concerts_by_day:
                            concerts_by_day[date] = []
                        concerts_by_day[date].append(concert)
                    
                    # Сортируем дни
                    sorted_days = sorted(concerts_by_day.keys(), key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
                    
                    concerts_text = ""
                    day_counter = 1
                    
                    print(concert)
                    for day in sorted_days:
                        day_concerts = concerts_by_day[day]
                        # Сортируем концерты в дне по времени
                        day_concerts.sort(key=lambda x: x['time'])
                        
                        concerts_text += f"🎈 *День {day_counter}* ({day})\n"
                        # concerts_text += "─" * 20 + "\n"
                        # concerts_text += "~" * 20 + "\n"
                        concerts_text += " " * 20 + "\n"
                        
                        for i, concert in enumerate(day_concerts, 1):
                            concerts_text += f"*{concert['time']}* • {concert['id']}. {concert['name']}\n"
                            # concerts_text += f"        {concert['hall']} • {concert['genre']}\n"
                            # concerts_text += f"🎵 **#{concert['id']} {concert['name']}**\n"
                            # concerts_text += f"   🕐 {concert['time']} • ⏱️ {concert['duration']}\n"
                            # concerts_text += f"   🏛️ {concert['hall']}\n"
                            # concerts_text += f"   🎭 {concert['genre']}\n"
                            
                            #Добавляем разделитель между концертами, но не после последнего
                            # if i < len(day_concerts):
                            #     # concerts_text += "   " + "─" * 25 + "\n"
                            #     concerts_text += "\n"
                        
                        concerts_text += "\n\n"
                        day_counter += 1
                    
                    personalized = personalized.replace("{route_concerts_list}", concerts_text.strip())
                else:
                    personalized = personalized.replace("{route_concerts_list}", "Маршрут не найден или пуст")
            
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
    def create_template(session: Session, name: str, content: str, variables: str = "", is_active: bool = True) -> MessageTemplate:
        """Создает новый шаблон"""
        template = MessageTemplate(
            name=name,
            content=content,
            variables=variables,
            is_active=is_active
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
        
        campaign_id = str(campaign.id)
        
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
            session.flush()  # Получаем ID без коммита
            
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
        
        # Обновляем статистику в кампании
        try:
            campaign_id_int = int(campaign_id)
            campaign = session.exec(
                select(TelegramCampaign).where(TelegramCampaign.id == campaign_id_int)
            ).first()
        except ValueError:
            campaign = None
        
        if campaign:
            campaign.sent_count = stats["sent"]
            campaign.delivered_count = stats["delivered"]
            campaign.failed_count = stats["failed"]
            session.add(campaign)
            session.commit()
        
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
    
 