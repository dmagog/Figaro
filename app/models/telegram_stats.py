from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class MessageStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"

class MessageTemplate(SQLModel, table=True):
    """Шаблоны сообщений для Telegram рассылок"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="Название шаблона")
    content: str = Field(description="Содержимое шаблона с переменными")
    variables: str = Field(default="", description="JSON строка с описанием переменных")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class TelegramMessage(SQLModel, table=True):
    """Записи о отправленных Telegram сообщениях"""
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(description="ID пользователя в Telegram")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    message_text: str = Field(description="Текст сообщения")
    file_path: Optional[str] = Field(default=None, description="Путь к прикрепленному файлу")
    file_type: Optional[str] = Field(default=None, description="Тип файла")
    parse_mode: Optional[str] = Field(default=None, description="Режим парсинга (Markdown/HTML)")
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    error_message: Optional[str] = Field(default=None, description="Сообщение об ошибке")
    sent_at: Optional[datetime] = Field(default=None, description="Время отправки")
    delivered_at: Optional[datetime] = Field(default=None, description="Время доставки")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    campaign_id: Optional[str] = Field(default=None, description="ID кампании для группировки")

class TelegramCampaign(SQLModel, table=True):
    """Кампании Telegram рассылок"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, description="Название кампании")
    description: Optional[str] = Field(default=None, description="Описание кампании")
    template_id: Optional[int] = Field(default=None, foreign_key="messagetemplate.id")
    target_users_count: int = Field(default=0, description="Количество целевых пользователей")
    sent_count: int = Field(default=0, description="Количество отправленных")
    delivered_count: int = Field(default=0, description="Количество доставленных")
    failed_count: int = Field(default=0, description="Количество неудачных")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = Field(default=None, description="Запланированное время отправки")
    sent_at: Optional[datetime] = Field(default=None, description="Время начала отправки")
    completed_at: Optional[datetime] = Field(default=None, description="Время завершения")
    is_active: bool = Field(default=True) 