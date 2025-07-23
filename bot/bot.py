import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ParseMode
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

@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
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
        await message.reply("✅ Ваш Telegram успешно привязан к аккаунту! Теперь вы будете получать уведомления о маршруте и концертах.")

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

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True) 