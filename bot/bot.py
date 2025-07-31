import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from sqlmodel import Session, select
from app.models.user import User, TelegramLinkCode
from app.database.simple_engine import simple_engine
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/Figaro_FestivalBot")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)

# Создаем клавиатуры
def get_main_menu_keyboard():
    """Создает основное меню с кнопками"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎵 Мой маршрут", callback_data="my_route"),
        InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
        InlineKeyboardButton("🎼 Концерты сегодня", callback_data="today_concerts"),
        InlineKeyboardButton("🏛️ Залы", callback_data="halls"),
        InlineKeyboardButton("🎭 Жанры", callback_data="genres"),
        InlineKeyboardButton("👤 Мой профиль", callback_data="profile"),
        InlineKeyboardButton("❓ Помощь", callback_data="help"),
        InlineKeyboardButton("🔗 Личный кабинет", callback_data="web_profile")
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
        InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
    )
    return keyboard

def get_day_selection_keyboard():
    """Создает клавиатуру для выбора дня"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    # Добавим кнопки для дней 1-5 (можно расширить)
    for day in range(1, 6):
        keyboard.add(InlineKeyboardButton(f"День {day}", callback_data=f"day_{day}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="route_menu"))
    return keyboard

@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == message.from_user.id)).first()
        if user:
            # Пользователь привязан - показываем меню
            await message.reply(
                f"👋 Привет, {user.name or 'друг'}! Я бот фестиваля 'Безумные дни'.\n\nВыберите действие:",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            # Пользователь не привязан - просим код
            await message.reply(
                "👋 Привет! Я бот фестиваля 'Безумные дни'.\n\nЧтобы привязать свой аккаунт, отправьте мне код привязки из личного кабинета на сайте.",
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
    
    with Session(simple_engine) as session:
        user = session.exec(select(User).where(User.telegram_id == callback_query.from_user.id)).first()
        if not user:
            await bot.send_message(callback_query.from_user.id, "❌ Ваш Telegram не привязан к аккаунту.")
            return
        
        action = callback_query.data
        
        if action == "main_menu":
            await bot.edit_message_text(
                f"👋 Привет, {user.name or 'друг'}! Выберите действие:",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action == "my_route":
            await bot.edit_message_text(
                "🎵 Выберите формат маршрута:",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_route_menu_keyboard()
            )
        
        elif action == "route_menu":
            await bot.edit_message_text(
                "🎵 Выберите формат маршрута:",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_route_menu_keyboard()
            )
        
        elif action == "route_brief":
            # Получаем краткий маршрут
            try:
                from app.services.telegram_service import TelegramService
                user_data = TelegramService.get_user_data(user, session)
                template = "{route_concerts_list}"
                message_text = TelegramService.personalize_message(template, user_data)
                await bot.edit_message_text(
                    message_text,
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
            except Exception as e:
                await bot.edit_message_text(
                    f"❌ Ошибка при получении маршрута: {str(e)}",
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
        
        elif action == "route_detailed":
            # Получаем развернутый маршрут
            try:
                from app.services.telegram_service import TelegramService
                user_data = TelegramService.get_user_data(user, session)
                template = "{route_concerts_list:detailed}"
                message_text = TelegramService.personalize_message(template, user_data)
                await bot.edit_message_text(
                    message_text,
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
            except Exception as e:
                await bot.edit_message_text(
                    f"❌ Ошибка при получении маршрута: {str(e)}",
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
        
        elif action == "route_stats":
            # Получаем статистику маршрута
            try:
                from app.services.telegram_service import TelegramService
                user_data = TelegramService.get_user_data(user, session)
                template = "{route_summary}"
                message_text = TelegramService.personalize_message(template, user_data)
                await bot.edit_message_text(
                    message_text,
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
            except Exception as e:
                await bot.edit_message_text(
                    f"❌ Ошибка при получении статистики: {str(e)}",
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_route_menu_keyboard()
                )
        
        elif action == "route_day":
            # Показываем выбор дня
            await bot.edit_message_text(
                "📅 Выберите день фестиваля:",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_day_selection_keyboard()
            )
        
        elif action.startswith("day_"):
            # Получаем маршрут на конкретный день
            day_number = action.split("_")[1]
            try:
                from app.services.telegram_service import TelegramService
                user_data = TelegramService.get_user_data(user, session)
                template = f"{{route_concerts_list:day={day_number}}}"
                message_text = TelegramService.personalize_message(template, user_data)
                await bot.edit_message_text(
                    message_text,
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_day_selection_keyboard()
                )
            except Exception as e:
                await bot.edit_message_text(
                    f"❌ Ошибка при получении маршрута на день {day_number}: {str(e)}",
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_day_selection_keyboard()
                )
        
        elif action == "statistics":
            # Получаем общую статистику
            try:
                from app.services.telegram_service import TelegramService
                user_data = TelegramService.get_user_data(user, session)
                template = "{route_summary}"
                message_text = TelegramService.personalize_message(template, user_data)
                await bot.edit_message_text(
                    message_text,
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_main_menu_keyboard()
                )
            except Exception as e:
                await bot.edit_message_text(
                    f"❌ Ошибка при получении статистики: {str(e)}",
                    callback_query.from_user.id,
                    callback_query.message.message_id,
                    reply_markup=get_main_menu_keyboard()
                )
        
        elif action == "profile":
            # Показываем профиль пользователя
            profile_text = f"👤 *Ваш профиль:*\n\n"
            profile_text += f"📧 Email: {user.email}\n"
            profile_text += f"👤 Имя: {user.name or 'Не указано'}\n"
            profile_text += f"🆔 ID: {user.id}\n"
            if user.telegram_username:
                profile_text += f"📱 Telegram: @{user.telegram_username}\n"
            
            await bot.edit_message_text(
                profile_text,
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action == "help":
            help_text = "❓ *Помощь по боту:*\n\n"
            help_text += "🎵 *Мой маршрут* - просмотр вашего маршрута фестиваля\n"
            help_text += "📊 *Статистика* - итоговая статистика маршрута\n"
            help_text += "🎼 *Концерты сегодня* - концерты на сегодня\n"
            help_text += "🏛️ *Залы* - информация о залах\n"
            help_text += "🎭 *Жанры* - информация о жанрах\n"
            help_text += "👤 *Мой профиль* - информация о вашем аккаунте\n"
            help_text += "🔗 *Личный кабинет* - ссылка на веб-версию\n\n"
            help_text += "Для привязки аккаунта используйте код из личного кабинета."
            
            await bot.edit_message_text(
                help_text,
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action == "web_profile":
            # Ссылка на личный кабинет
            web_url = "http://localhost:8000/profile"  # Можно сделать настраиваемым
            await bot.edit_message_text(
                f"🔗 *Личный кабинет:*\n\nПерейдите по ссылке для доступа к полному функционалу:\n{web_url}",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_main_menu_keyboard()
            )
        
        elif action in ["today_concerts", "halls", "genres"]:
            # Заглушки для будущих функций
            await bot.edit_message_text(
                "🚧 Эта функция находится в разработке. Скоро будет доступна!",
                callback_query.from_user.id,
                callback_query.message.message_id,
                reply_markup=get_main_menu_keyboard()
            )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True) 