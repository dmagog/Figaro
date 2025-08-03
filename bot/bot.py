import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import create_engine, text
from sqlmodel import Session, select
from app.database.simple_engine import simple_engine
from app.models.user import User, TelegramLinkCode
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SITE_LINK = os.getenv("SITE_LINK")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/Figaro_FestivalBot")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher(bot)

# Создаем клавиатуры
def get_main_menu_keyboard():
    """Создает основное меню с кнопками"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🗺️ Мой маршрут", callback_data="my_route"),
        InlineKeyboardButton("🚶🏼‍➡️ Офф-программа", callback_data="offprog"),
        InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        InlineKeyboardButton("🎼 Концерты сегодня", callback_data="today_concerts"),
        InlineKeyboardButton("🏛️ Залы", callback_data="halls"),
        InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        InlineKeyboardButton("❓ Помощь", callback_data="help"),
        InlineKeyboardButton("🔗 Личный кабинет", callback_data="web_profile"),
        InlineKeyboardButton("🌐 Сайт фестиваля", callback_data="site_official")
    )
    return keyboard

def get_route_menu_keyboard():
    """Создает меню для работы с маршрутом"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 Краткий маршрут", callback_data="route_brief"),
        InlineKeyboardButton("📖 Развернутый маршрут", callback_data="route_detailed"),
        InlineKeyboardButton("📊 Статистика маршрута", callback_data="route_stats"),
        InlineKeyboardButton("📅 Маршрут на день", callback_data="route_day"),
        InlineKeyboardButton("«« Назад", callback_data="main_menu")
    )
    return keyboard

async def get_day_selection_keyboard(telegram_id: int):
    """Создает клавиатуру для выбора дня на основе реальных данных маршрута"""
    try:
        # Получаем список доступных дней
        result = await api_client.get_route_days(telegram_id)
        if "error" in result:
            # Если ошибка, возвращаем пустую клавиатуру с кнопкой назад
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("«« Назад", callback_data="route_menu"))
            return keyboard
        
        days = result.get("days", [])
        if not days:
            # Если нет дней, показываем сообщение
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="route_menu"))
            return keyboard
        
        # Создаем клавиатуру с реальными днями
        keyboard = InlineKeyboardMarkup(row_width=2)
        for day_info in days:
            day_number = day_info["day_number"]
            formatted_date = day_info["formatted_date"]
            concerts_count = day_info["concerts_count"]
            button_text = f"День {day_number} ({formatted_date}) - {concerts_count} конц."
            keyboard.add(InlineKeyboardButton(button_text, callback_data=f"day_{day_number}"))
        
        keyboard.add(InlineKeyboardButton("«« Назад", callback_data="route_menu"))
        return keyboard
        
    except Exception as e:
        print(f"Ошибка при создании клавиатуры дней: {e}")
        # Возвращаем простую клавиатуру с кнопкой назад
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("«« Назад", callback_data="route_menu"))
        return keyboard

from services.api_client import ApiClient

# Создаем экземпляр API клиента
api_client = ApiClient()

def escape_markdown(text):
    """Экранирует специальные символы Markdown"""
    if not text:
        return text
    # Экранируем символы, которые могут сломать Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def send_template_message_async(template_id: int, telegram_id: int):
    """Отправляет сообщение пользователю по шаблону через HTTP API и Celery"""
    try:
        return await api_client.send_template_message(telegram_id, template_id)
    except Exception as e:
        print(f"Ошибка при отправке шаблонного сообщения: {e}")
        return {"error": f"Ошибка сети: {str(e)}"}

def format_route_concerts_list(concerts_data, detailed=False, day_number=None):
    """Форматирует список концертов для отображения"""
    try:
        sorted_concerts = concerts_data.get("sorted_concerts", [])
        if not sorted_concerts:
            return "Маршрут не найден или пуст"
        
        # Группируем концерты по дням
        concerts_by_day = {}
        for i, concert_data in enumerate(sorted_concerts):
            concert = concert_data['concert']
            if concert.get('datetime'):
                # Проверяем, является ли datetime строкой или объектом
                if isinstance(concert['datetime'], str):
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(concert['datetime'].replace('Z', '+00:00'))
                    except:
                        # Если не удается распарсить, пропускаем концерт
                        continue
                else:
                    dt = concert['datetime']
                
                day = dt.date()
                if day not in concerts_by_day:
                    concerts_by_day[day] = []
                concerts_by_day[day].append({
                    'index': i + 1,
                    'time': dt.strftime("%H:%M"),
                    'name': escape_markdown(concert.get('name', 'Название не указано')),
                    'hall': escape_markdown(concert.get('hall', {}).get('name', 'Зал не указан')),
                    'duration': escape_markdown(str(concert.get('duration', 'Длительность не указана'))),
                    'genre': escape_markdown(concert.get('genre', 'Жанр не указан')),
                    'concert_data': concert_data
                })
        
        # Сортируем дни
        sorted_days = sorted(concerts_by_day.keys())
        
        if day_number:
            # Показываем только конкретный день
            try:
                day_index = int(day_number) - 1
                if 0 <= day_index < len(sorted_days):
                    target_day = sorted_days[day_index]
                    day_concerts = concerts_by_day[target_day]
                    
                    # Форматируем дату
                    day_str = str(target_day.day)
                    month_names = {
                        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                        5: "мая", 6: "июня", 7: "июля", 8: "августа",
                        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
                    }
                    month_str = month_names.get(target_day.month, "месяца")
                    
                    concerts_text = f"🎈 *День {day_index + 1}* ({day_str} {month_str})\n\n"
                    
                    for concert in day_concerts:
                        if detailed:
                            concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                            concerts_text += f"🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                            
                            if concert['concert_data'].get('transition_info'):
                                transition = concert['concert_data']['transition_info']
                                if transition.get('status') == 'success':
                                    concerts_text += f"🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                                elif transition.get('status') == 'same_hall':
                                    concerts_text += f"📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                            
                            concerts_text += "\n"
                        else:
                            concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
                    
                    return concerts_text
                else:
                    return f"День {day_number} не найден в маршруте"
            except ValueError:
                return f"Неверный номер дня: {day_number}"
        
        # Показываем все дни
        concerts_text = ""
        for day_index, target_day in enumerate(sorted_days, 1):
            day_concerts = concerts_by_day[target_day]
            
            # Форматируем дату
            day_str = str(target_day.day)
            month_names = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
            }
            month_str = month_names.get(target_day.month, "месяца")
            
            concerts_text += f"🎈 *День {day_index}* ({day_str} {month_str})\n\n"
            
            for concert in day_concerts:
                if detailed:
                    concerts_text += f"*{concert['time']}* • {concert['index']}. {concert['name']}\n"
                    concerts_text += f"🏛️ {concert['hall']} • ⏱️ {concert['duration']} • 🎭 {concert['genre']}\n"
                    
                    if concert['concert_data'].get('transition_info'):
                        transition = concert['concert_data']['transition_info']
                        if transition.get('status') == 'success':
                            concerts_text += f"🚶🏼‍➡️ Переход в другой зал: ~{transition.get('walk_time', 0)} мин • {transition.get('time_between', 0)} мин до следующего\n"
                        elif transition.get('status') == 'same_hall':
                            concerts_text += f"📍 Остаёмся в том же зале • {transition.get('time_between', 0)} мин до следующего\n"
                    
                    concerts_text += "\n"
                else:
                    concerts_text += f"{concert['time']} • {concert['index']}. {concert['name']}\n"
            
            concerts_text += "\n"
        
        return concerts_text.strip()
        
    except Exception as e:
        print(f"Ошибка при форматировании маршрута: {e}")
        return f"Ошибка при форматировании: {str(e)}"

def format_route_summary(concerts_data):
    """Форматирует статистику маршрута"""
    try:
        route_summary = concerts_data.get("route_summary", {})
        if not route_summary:
            return "Статистика маршрута недоступна"
        
        summary_text = "📊 *Итоговая статистика маршрута:*\n\n"
        
        # Основные показатели
        summary_text += f"🎵 *Концертов:* {route_summary.get('total_concerts', 0)}\n"
        summary_text += f"📅 *Дней:* {route_summary.get('total_days', 0)}\n"
        summary_text += f"🏛️ *Залов:* {route_summary.get('total_halls', 0)}\n"
        summary_text += f"🎨 *Жанров:* {route_summary.get('total_genres', 0)}\n"
        
        # Время
        concert_time = route_summary.get('total_concert_time_minutes', 0)
        if concert_time:
            summary_text += f"⏱️ *Время концертов:* {concert_time} мин\n"
        
        trans_time = route_summary.get('total_walk_time_minutes', 0)
        if trans_time:
            summary_text += f"🚶 *Время переходов:* {trans_time} мин\n"
        
        # Расстояние
        distance = route_summary.get('total_distance_km', 0)
        if distance:
            summary_text += f"📍 *Пройдено:* {distance} км\n"
        
        # Контент
        compositions = route_summary.get('unique_compositions', 0)
        if compositions:
            summary_text += f"🎼 *Произведений:* {compositions}\n"
        
        authors = route_summary.get('unique_authors', 0)
        if authors:
            summary_text += f"✍️ *Авторов:* {authors}\n"
        
        artists = route_summary.get('unique_artists', 0)
        if artists:
            summary_text += f"🎭 *Артистов:* {artists}\n"
        
        summary_text += "\n🎉 *Спасибо, что выбрали наш фестиваль! До встречи на концертах!*"
        
        return summary_text
        
    except Exception as e:
        print(f"Ошибка при форматировании статистики: {e}")
        return f"Ошибка при форматировании статистики: {str(e)}"

@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            # Пользователь привязан - показываем меню
            await message.reply(
                f"""Привет, {user.name or 'друг'}! 👋 \n\n
Я *Figaro* — твой помощник на фестивале _«Безумные дни в Екатеринбурге»_. 
С моей помощью фестиваль будет как на ладони: маршрутный лист перед глазами, билеты всегда под рукой и 
своевременные напоминания о событиях.\n\n
Выбери действие:
                """,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Пользователь не привязан - просим код
            await message.reply(
                """Привет! Я *Figaro* — твой помощник на фестивале _«Безумные дни в Екатеринбурге»_.\n\n
Чтобы воспользоваться всеми возможностями, привяжи свой аккакаунт. Для этого:\n\n
1\. Перейди в личный кабинет на моём сайте\n
2\. Скопируй уникальный код, по которому я тебя узнаю\n
3\. Отправь мне этот код в сообщении
                """,
                reply=False
            )

@dp.message_handler(lambda m: len(m.text.strip()) >= 10 and len(m.text.strip()) <= 50)
async def handle_link_code(message: types.Message):
    code = message.text.strip()
    with Session(simple_engine) as session:
        now = datetime.utcnow()
        link_code = session.exec(
            select(TelegramLinkCode)
            .where(TelegramLinkCode.code == code)
            .where(TelegramLinkCode.expires_at > now)
        ).first()
        if not link_code:
            await message.reply("❌ Код не найден или истёк. Проверьте правильность и попробуйте снова.")
            return
        user = session.get(User, link_code.user_id)
        if not user:
            await message.reply("❌ Пользователь не найден. Обратитесь в поддержку.")
            return
        # Привязываем telegram_id и username
        user.telegram_id = message.from_user.id
        if hasattr(message.from_user, 'username') and message.from_user.username:
            user.telegram_username = message.from_user.username
        else:
            user.telegram_username = None
        session.add(user)
        # Удаляем использованный код
        session.delete(link_code)
        session.commit()
        await message.reply(
            "✅ Ваш Telegram успешно привязан к аккаунту! Теперь вы можете использовать меню бота.",
            reply_markup=get_main_menu_keyboard()
        )

@dp.message_handler(commands=["whoami"])
async def whoami(message: types.Message):
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            await message.reply(f"Вы привязаны к аккаунту: {user.email}\nВаше имя: {user.name or '-'}")
        else:
            await message.reply("Ваш Telegram не привязан к аккаунту. Сначала выполните привязку через личный кабинет.")

@dp.message_handler(commands=["testmsg"])
async def testmsg(message: types.Message):
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            await message.reply("✅ Тестовое сообщение: связь с ботом работает!")
        else:
            await message.reply("❌ Ваш Telegram не привязан к аккаунту. Сначала выполните привязку через личный кабинет.")

# Обработчики для callback-кнопок
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    
    async def safe_edit_message(text, reply_markup=None, parse_mode=None):
        """Безопасное редактирование сообщения с обработкой ошибок"""
        try:
            await bot.edit_message_text(
                text,
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            if "Message is not modified" in str(e):
                # Игнорируем ошибку если сообщение не изменилось
                pass
            elif "Can't parse entities" in str(e) and parse_mode == 'Markdown':
                # Если не удается распарсить Markdown, пробуем без него
                try:
                    await bot.edit_message_text(
                        text,
                        callback_query.from_user.id,
                        callback_query.message.message_id,
                        reply_markup=reply_markup,
                        parse_mode=None
                    )
                except Exception as e2:
                    # Если и это не работает, отправляем новое сообщение
                    await bot.send_message(
                        callback_query.from_user.id,
                        text,
                        reply_markup=reply_markup,
                        parse_mode=None
                    )
            else:
                # Отправляем новое сообщение если редактирование не удалось
                await bot.send_message(
                    callback_query.from_user.id,
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
    
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == callback_query.from_user.id)).first()
        if not user:
            await bot.send_message(callback_query.from_user.id, "❌ Ваш Telegram не привязан к аккаунту.")
            return
        
        action = callback_query.data
        
        if action == "main_menu":
            await safe_edit_message(
                f"👋 Привет, {user.name or 'друг'}! Выберите действие:",
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action == "my_route":
            await safe_edit_message(
                """🎵 Выберите формат маршрута:\n\n
• *Краткий* — коротко и наглядно\n
• *Полный* — развернуто и информативно
                """,
                reply_markup=get_route_menu_keyboard()
            )
        
        elif action == "route_menu":
            await safe_edit_message(
                """🗺️ Выберите формат маршрута:\n\n
• *Краткий* — коротко и наглядно\n
• *Полный* — развернуто и информативно
                """,
                reply_markup=get_route_menu_keyboard()
            )
        
        elif action == "route_brief":
            # Получаем и отображаем краткий маршрут
            await safe_edit_message("🔄 Загружаю ваш маршрут...")
            try:
                result = await api_client.get_route_data(callback_query.from_user.id)
                if "error" in result:
                    await safe_edit_message(f"❌ Ошибка: {result['error']}", reply_markup=get_route_menu_keyboard())
                else:
                    route_data = result.get("route_data", {})
                    formatted_route = format_route_concerts_list(route_data, detailed=False)
                    await safe_edit_message(f"🎵 *Ваш краткий маршрут:*\n\n{formatted_route}", 
                                          reply_markup=get_route_menu_keyboard(), parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при получении маршрута: {e}")
                await safe_edit_message("❌ Ошибка сети. Попробуйте позже.", reply_markup=get_route_menu_keyboard())
        
        elif action == "route_detailed":
            # Получаем и отображаем развернутый маршрут
            await safe_edit_message("🔄 Загружаю развернутый маршрут...")
            try:
                result = await api_client.get_route_data(callback_query.from_user.id)
                if "error" in result:
                    await safe_edit_message(f"❌ Ошибка: {result['error']}", reply_markup=get_route_menu_keyboard())
                else:
                    route_data = result.get("route_data", {})
                    formatted_route = format_route_concerts_list(route_data, detailed=True)
                    await safe_edit_message(f"🎵 *Ваш развернутый маршрут:*\n\n{formatted_route}", 
                                          reply_markup=get_route_menu_keyboard(), parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при получении развернутого маршрута: {e}")
                await safe_edit_message("❌ Ошибка сети. Попробуйте позже.", reply_markup=get_route_menu_keyboard())
        
        elif action == "route_stats":
            # Получаем и отображаем статистику маршрута
            await safe_edit_message("🔄 Загружаю статистику маршрута...")
            try:
                result = await api_client.get_route_data(callback_query.from_user.id)
                if "error" in result:
                    await safe_edit_message(f"❌ Ошибка: {result['error']}", reply_markup=get_route_menu_keyboard())
                else:
                    route_data = result.get("route_data", {})
                    formatted_stats = format_route_summary(route_data)
                    await safe_edit_message(f"📊 *Статистика вашего маршрута:*\n\n{formatted_stats}", 
                                          reply_markup=get_route_menu_keyboard(), parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при получении статистики маршрута: {e}")
                await safe_edit_message("❌ Ошибка сети. Попробуйте позже.", reply_markup=get_route_menu_keyboard())
        
        elif action == "route_day":
            # Показываем выбор дня
            await safe_edit_message("📅 Загружаю доступные дни...")
            keyboard = await get_day_selection_keyboard(callback_query.from_user.id)
            await safe_edit_message(
                "📅 Выберите день фестиваля:",
                reply_markup=keyboard
            )
        
        elif action.startswith("day_"):
            # Получаем и отображаем маршрут на конкретный день
            day_number = action.split("_")[1]
            await safe_edit_message(f"🔄 Загружаю маршрут на день {day_number}...")
            try:
                result = await api_client.get_route_day(callback_query.from_user.id, int(day_number))
                if "error" in result:
                    keyboard = await get_day_selection_keyboard(callback_query.from_user.id)
                    await safe_edit_message(f"❌ Ошибка: {result['error']}", reply_markup=keyboard)
                else:
                    formatted_route = result.get("formatted_route", "Маршрут не найден")
                    keyboard = await get_day_selection_keyboard(callback_query.from_user.id)
                    await safe_edit_message(f"📅 *Маршрут на день {day_number}:*\n\n{formatted_route}", 
                                          reply_markup=keyboard, parse_mode='Markdown')
            except Exception as e:
                print(f"Ошибка при получении маршрута на день: {e}")
                keyboard = await get_day_selection_keyboard(callback_query.from_user.id)
                await safe_edit_message("❌ Ошибка сети. Попробуйте позже.", reply_markup=keyboard)
        
        elif action == "statistics":
            # Отправляем общую статистику по шаблону
            await safe_edit_message("🔄 Отправляю общую статистику...")
            result = await send_template_message_async(5, callback_query.from_user.id)  # ID шаблона для общей статистики
            if "error" in result:
                await safe_edit_message(f"❌ Ошибка: {result['error']}", reply_markup=get_main_menu_keyboard())
            else:
                await safe_edit_message("✅ Общая статистика отправлена в личные сообщения!", reply_markup=get_main_menu_keyboard())
        
        elif action == "profile":
            # Показываем профиль пользователя
            profile_text = f"👤 *Ваш профиль:*\n\n"
            profile_text += f"📧 Email: {user.email}\n"
            profile_text += f"👤 Имя: {user.name or 'Не указано'}\n"
            profile_text += f"🆔 ID: {user.id}\n"
            if user.telegram_username:
                profile_text += f"📱 Telegram: @{user.telegram_username}\n"
            
            await safe_edit_message(
                profile_text,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action == "help":
            help_text = "*Что есть что❓:*\n\n"
            help_text += "🗺️ *Мой маршрут* — все концерты по порядку: кратко и наглядно, или развернуто и информативно\n\n"
            help_text += "📊 *Статистика* — ваш маршрут в цифрах и любопытных фактах\n\n"
            help_text += "🎼 *Концерты сегодня* — маршрут этого дня\n\n"
            help_text += "🏛️ *Залы* — где находятся и как их найти\n\n"
            help_text += "👤 *Мой профиль* — убедиться, что Вы это Вы\n\n"
            help_text += "🔗 *Личный кабинет* — ссылка на веб\-версию\n\n"
            help_text += "Для привязки аккаунта используйте код из личного кабинета\."
            
            await safe_edit_message(
                help_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        
        elif action == "web_profile":
            # Ссылка на личный кабинет
            web_url = SITE_LINK + "/profile"  # Можно сделать настраиваемым
            # Создаем безопасную ссылку без специальных символов
            safe_url = web_url.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('-', '\\-')
            print(f"Debug: Original URL: {web_url}")
            print(f"Debug: Safe URL: {safe_url}")
            
            # Пробуем сначала с Markdown
            try:
                await safe_edit_message(
                    f"""🔗 *Личный кабинет*\n
Функции, которые будут удобнее в веб\-версии сервиса:
• Маршрутный лист
• Детальная статистика
• Настройки уведомлений

[Перейти в личный кабинет]({safe_url})
                    """,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Markdown failed, trying HTML: {e}")
                # Если Markdown не работает, пробуем HTML
                await safe_edit_message(
                    f"""🔗 <b>Личный кабинет</b>\n
Функции, которые будут удобнее в веб-версии сервиса:
• Маршрутный лист
• Детальная статистика
• Настройки уведомлений

<a href="{web_url}">Перейти в личный кабинет</a>
                    """,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode='HTML'
                )
        
        elif action in ["today_concerts", "halls", "genres"]:
            # Заглушки для будущих функций
            await safe_edit_message(
                "🚧 Эта функция находится в разработке. Скоро будет доступна!",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )

if __name__ == "__main__":
    import asyncio
    import time
    
    while True:
        try:
            print("Запуск бота...")
            executor.start_polling(dp, skip_updates=True)
        except Exception as e:
            print(f"Ошибка в работе бота: {e}")
            print("Перезапуск через 30 секунд...")
            time.sleep(30) 