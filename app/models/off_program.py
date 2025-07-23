from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class EventFormat(str, Enum):
    """Форматы мероприятий Офф-программы"""
    CONSULTATION = "Консультация"
    WORKSHOP = "Воркшоп"
    BROADCAST = "Трансляция"
    LECTURE = "Лекция"
    MASTERCLASS = "Мастер-класс"
    EVENT = "Событие"  # Добавлено для поддержки формата 'Событие'


class OffProgram(SQLModel, table=True, extend_existing=True):
    """Модель данных для мероприятий Офф-программы фестиваля"""
    
    __tablename__ = "off_program"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Основная информация о мероприятии
    event_num: int = Field(description="Номер мероприятия")
    event_name: str = Field(description="Название мероприятия")
    description: Optional[str] = Field(default=None, description="Описание мероприятия")
    
    # Время и дата
    event_date: datetime = Field(description="Дата и время проведения")
    event_long: str = Field(description="Продолжительность мероприятия (формат HH:MM:SS)")
    
    # Место проведения
    hall_name: str = Field(description="Название зала/места проведения")
    
    # Формат и рекомендации
    format: Optional[EventFormat] = Field(default=None, description="Формат мероприятия")
    recommend: bool = Field(default=False, description="Рекомендуемое мероприятие")
    
    # Дополнительная информация
    link: Optional[str] = Field(default=None, description="Ссылка на дополнительную информацию")
    
    class Config:
        schema_extra = {
            "example": {
                "event_num": 1,
                "event_name": "Консультации, продажа билетов/абонементов",
                "description": "Консультации по покупке билетов и абонементов",
                "event_date": "2022-07-01T10:00:00",
                "event_long": "11:00:00",
                "hall_name": "Инфоцентр",
                "format": "Консультация",
                "recommend": False,
                "link": None
            }
        } 