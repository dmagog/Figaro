from app.database.database import get_session
from app.models.telegram_stats import MessageTemplate
from sqlmodel import select

session = next(get_session())

# Находим шаблон "Напоминание о следующем концерте"
template = session.exec(
    select(MessageTemplate).where(MessageTemplate.name.like('%следующем концерте%'))
).first()

if template:
    # Обновляем содержимое шаблона с правильными переменными
    template.content = '''🎵 **Напоминание о концерте №{next_concert_number}, {name}!**

🎼 **{next_concert_name}**
📅 Дата: {next_concert_date}
🕐 Время: {next_concert_time}
🏛️ Зал: {next_concert_hall}
⏱️ Длительность: {next_concert_duration}

🎭 **Артисты:**
{next_concert_artists}

🎼 **Произведения:**
{next_concert_compositions}

{transition_info}

Удачного концерта! 🎉'''
    
    session.add(template)
    session.commit()
    print(f'Шаблон "{template.name}" обновлен')
else:
    print('Шаблон не найден') 