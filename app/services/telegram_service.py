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
        },
        {
            "name": "Напоминание о концерте по позиции",
            "content": "🎵 Напоминание о концерте №{concert_position:1}, {name}!\n\n🎼 {next_concert_name}\n📅 Дата: {next_concert_date}\n🕐 Время: {next_concert_time}\n🏛️ Зал: {next_concert_hall}\n⏱️ Длительность: {next_concert_duration}\n\n🎭 Артисты:\n{next_concert_artists}\n\n🎼 Произведения:\n{next_concert_compositions}\n\nУдачного концерта! 🎉",
            "variables": '{"name": "Имя пользователя", "concert_position:N": "Номер концерта в маршруте (например: {concert_position:1} для первого концерта)", "next_concert_name": "Название концерта", "next_concert_date": "Дата концерта", "next_concert_time": "Время концерта", "next_concert_hall": "Название зала", "next_concert_duration": "Длительность концерта", "next_concert_artists": "Список артистов", "next_concert_compositions": "Список произведений с авторами"}'
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
            "route_summary": {},
            "concerts_for_template": []
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
            
            # Получаем маршрут пользователя используя простую логику сортировки
            try:
                from app.services.crud.purchase import get_user_unique_concerts_with_details
                from app.routes.user.temp_routes import calculate_transition_time
                
                # Получаем уникальные концерты пользователя
                concerts_data = get_user_unique_concerts_with_details(session, str(user.external_id))
                
                if concerts_data:
                    # Сортируем концерты по дате и времени
                    sorted_concerts = sorted(
                        concerts_data, 
                        key=lambda x: x['concert'].get('datetime') if x['concert'].get('datetime') else datetime.min
                    )
                    
                    # Создаем плоский список концертов
                    flat_concerts = []
                    flat_concerts_for_template = []
                    
                    for i, concert_data in enumerate(sorted_concerts):
                        concert = concert_data['concert']
                        
                        # Форматируем дату: число + месяц прописью
                        date_str = "Дата не указана"
                        if concert.get('datetime'):
                            month_names = {
                                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                            }
                            day = concert['datetime'].day
                            month = month_names.get(concert['datetime'].month, "месяца")
                            date_str = f"{day} {month}"
                        
                        # Базовая информация для route_concerts
                        flat_concerts.append({
                            "id": concert.get('id'),
                            "name": concert.get('name') or "Название не указано",
                            "date": date_str,
                            "time": concert['datetime'].strftime("%H:%M") if concert.get('datetime') else "Время не указано",
                            "hall": concert.get('hall', {}).get('name') if concert.get('hall') else "Зал не указан",
                            "duration": str(concert.get('duration')) if concert.get('duration') else "Длительность не указана",
                            "day_index": i + 1  # Простая нумерация
                        })
                        
                        # Полная информация для concerts_for_template
                        flat_concerts_for_template.append(concert_data)
                    
                    # Создаем простую сводку
                    route_summary = {
                        "total_concerts": len(flat_concerts),
                        "total_days": len(set(c['concert'].get('datetime', datetime.min).date() for c in sorted_concerts if c['concert'].get('datetime'))),
                        "total_halls": len(set(c['concert'].get('hall', {}).get('id') for c in sorted_concerts if c['concert'].get('hall'))),
                        "total_genres": len(set(c['concert'].get('genre') for c in sorted_concerts if c['concert'].get('genre'))),
                        "show_time": 0,
                        "trans_time": 0,
                        "wait_time": 0,
                        "comfort_score": 0,
                        "intellect_score": 0
                    }
                    
                    # Добавляем информацию о переходах для каждого концерта
                    for i, concert_data in enumerate(sorted_concerts):
                        if i < len(sorted_concerts) - 1:  # Если есть следующий концерт
                            next_concert_data = sorted_concerts[i + 1]
                            transition_info = calculate_transition_time(session, concert_data, next_concert_data)
                            flat_concerts_for_template[i]['transition_info'] = transition_info
                        else:
                            # Для последнего концерта нет перехода
                            flat_concerts_for_template[i]['transition_info'] = None
                    
                    data["route_concerts"] = flat_concerts
                    data["concerts_for_template"] = flat_concerts_for_template
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
                    # Группируем концерты по дням фестиваля
                    concerts_by_day = {}
                    for concert in route_concerts:
                        day_index = concert['day_index']
                        if day_index not in concerts_by_day:
                            concerts_by_day[day_index] = []
                        concerts_by_day[day_index].append(concert)
                    
                    # Сортируем дни по номеру фестивального дня
                    sorted_days = sorted(concerts_by_day.keys())
                    
                    concerts_text = ""
                    
                    for day_index in sorted_days:
                        day_concerts = concerts_by_day[day_index]
                        # Сортируем концерты в дне по времени
                        day_concerts.sort(key=lambda x: x['time'])
                        
                        # Берем дату из первого концерта дня
                        day_date = day_concerts[0]['date'] if day_concerts else "Дата не указана"
                        
                        concerts_text += f"🎈 *День {day_index}* ({day_date})\n"
                        concerts_text += " " * 20 + "\n"
                        
                        for i, concert in enumerate(day_concerts, 1):
                            concerts_text += f"*{concert['time']}* • {concert['id']}. {concert['name']}\n"
                        
                        concerts_text += "\n\n"
                    
                    personalized = personalized.replace("{route_concerts_list}", concerts_text.strip())
                else:
                    personalized = personalized.replace("{route_concerts_list}", "Маршрут не найден или пуст")
            
            # Специальная обработка для concert_position с номером
            import re
            concert_position_pattern = r'\{concert_position:(\d+)\}'
            
            # Собираем все замены для concert_position
            concert_replacements_to_apply = {}
            
            for match in re.finditer(concert_position_pattern, personalized):
                position = int(match.group(1))
                
                # Получаем концерт по указанной позиции
                route_concerts = user_data.get("route_concerts", [])
                concerts_for_template = user_data.get("concerts_for_template", [])
                
                if 1 <= position <= len(route_concerts):
                    concert_index = position - 1
                    concert = route_concerts[concert_index]
                    concert_data = concerts_for_template[concert_index] if concert_index < len(concerts_for_template) else None
                    
                    # Получаем артистов
                    artists = []
                    if concert_data and 'concert' in concert_data and 'artists' in concert_data['concert']:
                        for artist in concert_data['concert']['artists']:
                            artists.append(artist.get('name', 'Неизвестный артист'))
                    artists_text = "\n".join(artists) if artists else "Артисты не указаны"
                    
                    # Получаем произведения с авторами
                    compositions = []
                    if concert_data and 'concert' in concert_data and 'compositions' in concert_data['concert']:
                        for comp in concert_data['concert']['compositions']:
                            comp_name = comp.get('name', 'Неизвестное произведение')
                            author_name = comp.get('author', {}).get('name', 'Неизвестный автор') if comp.get('author') else 'Неизвестный автор'
                            compositions.append(f"• {comp_name} ({author_name})")
                    compositions_text = "\n".join(compositions) if compositions else "Произведения не указаны"
                    
                    # Формируем информацию о переходе
                    transition_info_text = ""
                    if concert_data and 'transition_info' in concert_data and concert_data['transition_info']:
                        transition = concert_data['transition_info']
                        time_between = transition.get('time_between', 0)
                        walk_time = transition.get('walk_time', 0)
                        status = transition.get('status', '')
                        
                        if status == 'same_hall':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Остаемся в том же зале"
                        elif status == 'same_building':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Переход в том же здании"
                        elif status == 'hurry':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Переход в другой зал: ~{walk_time} мин (нужно поторопиться!)"
                        elif status == 'tight':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Переход в другой зал: ~{walk_time} мин (впритык)"
                        elif status == 'success':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Переход в другой зал: ~{walk_time} мин (достаточно времени)"
                        elif status == 'overlap':
                            transition_info_text = f"⚠️ Наложение концертов! Текущий концерт заканчивается в {transition.get('current_end', '?')}, следующий начинается в {transition.get('next_start', '?')}"
                        elif status == 'no_transition_data':
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Время перехода неизвестно"
                        else:
                            transition_info_text = f"⏱️ {time_between} мин между концертами • Переход в другой зал: ~{walk_time} мин"
                    else:
                        transition_info_text = "⏱️ Информация о переходе недоступна"
                    
                    # Собираем замены для этого концерта
                    concert_replacements = {
                        "{next_concert_name}": concert.get('name', 'Концерт не найден'),
                        "{next_concert_date}": concert.get('date', 'Дата не указана'),
                        "{next_concert_time}": concert.get('time', 'Время не указано'),
                        "{next_concert_hall}": concert.get('hall', 'Зал не указан'),
                        "{next_concert_duration}": concert.get('duration', 'Длительность не указана'),
                        "{next_concert_artists}": artists_text,
                        "{next_concert_compositions}": compositions_text,
                        "{transition_info}": transition_info_text,
                    }
                    
                    # Добавляем в общий словарь замен
                    concert_replacements_to_apply.update(concert_replacements)
                    
                    # Заменяем саму переменную позиции
                    concert_replacements_to_apply[match.group(0)] = str(position)
                else:
                    # Если позиция неверная, заменяем на "не найдено"
                    concert_replacements_to_apply[match.group(0)] = "не найдено"
            
            # Применяем все замены за один раз
            for placeholder, value in concert_replacements_to_apply.items():
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
    
 