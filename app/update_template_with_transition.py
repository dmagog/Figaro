from database.database import get_session
from models.telegram_stats import MessageTemplate
from sqlmodel import select

session = next(get_session())
template = session.exec(select(MessageTemplate).where(MessageTemplate.name == 'Напоминание о следующем концерте')).first()

if template:
    template.content = """🎵 Напоминание о концерте №{concert_position:1}, {name}!

🎼 {next_concert_name}
📅 Дата: {next_concert_date}
🕐 Время: {next_concert_time}
🏛️ Зал: {next_concert_hall}
⏱️ Длительность: {next_concert_duration}

🎭 Артисты:
{next_concert_artists}

🎼 Произведения:
{next_concert_compositions}

{transition_info}

Удачного концерта! 🎉"""
    
    session.add(template)
    session.commit()
    print('Шаблон обновлен с информацией о переходе')
else:
    print('Шаблон не найден') 