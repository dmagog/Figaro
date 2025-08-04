import os
from aiogram import Bot
from aiogram.types import ParseMode, InputFile
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)

async def send_telegram_message(telegram_id: int, text: str = None, file_path: str = None, file_type: str = None, parse_mode: str = None):
    try:
        # Если parse_mode не указан, используем None (обычный текст)
        if parse_mode is None:
            parse_mode = None
        elif parse_mode.lower() == "markdown":
            parse_mode = ParseMode.MARKDOWN
        elif parse_mode.lower() == "html":
            parse_mode = ParseMode.HTML
            
        if file_path and file_type == 'photo':
            await bot.send_photo(chat_id=telegram_id, photo=InputFile(file_path), caption=text or "", parse_mode=parse_mode)
        elif file_path and file_type == 'document':
            await bot.send_document(chat_id=telegram_id, document=InputFile(file_path), caption=text or "", parse_mode=parse_mode)
        else:
            await bot.send_message(chat_id=telegram_id, text=text or "(пустое сообщение)", parse_mode=parse_mode)
        return True
    except Exception as e:
        print(f"[Telegram] Ошибка отправки сообщения: {e}")
        return False 