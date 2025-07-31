#!/usr/bin/env python3

from app.database.database import get_session
from app.models.telegram_stats import MessageTemplate
from sqlmodel import select

def update_template():
    session = next(get_session())
    
    # Удаляем старый шаблон
    old_template = session.exec(
        select(MessageTemplate).where(MessageTemplate.name == 'Напоминание о концерте по позиции')
    ).first()
    
    if old_template:
        session.delete(old_template)
        session.commit()
        print('Старый шаблон удален')
    
    # Создаем новый шаблон
    new_template = MessageTemplate(
        name="Напоминание о концерте по позиции",
        content="🎵 Напоминание о концерте №{concert_position:1}, {name}!\n\n🎼 {next_concert_name}\n📅 Дата: {next_concert_date}\n🕐 Время: {next_concert_time}\n🏛️ Зал: {next_concert_hall}\n⏱️ Длительность: {next_concert_duration}\n\n🎭 Артисты:\n{next_concert_artists}\n\n🎼 Произведения:\n{next_concert_compositions}\n\nУдачного концерта! 🎉",
        variables='{"name": "Имя пользователя", "concert_position:N": "Номер концерта в маршруте (например: {concert_position:1} для первого концерта)", "next_concert_name": "Название концерта", "next_concert_date": "Дата концерта", "next_concert_time": "Время концерта", "next_concert_hall": "Название зала", "next_concert_duration": "Длительность концерта", "next_concert_artists": "Список артистов", "next_concert_compositions": "Список произведений с авторами"}',
        is_active=True
    )
    
    session.add(new_template)
    session.commit()
    print('Новый шаблон создан')

if __name__ == "__main__":
    update_template() 