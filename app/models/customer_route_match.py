from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class CustomerRouteMatch(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_external_id: str = Field(index=True, description="Внешний ID покупателя")
    
    # Результат сопоставления
    found: bool = Field(description="Найдено ли соответствие")
    match_type: Optional[str] = Field(default=None, description="Тип совпадения: exact, partial, none")
    reason: Optional[str] = Field(default=None, description="Причина отсутствия совпадения")
    
    # Данные покупателя (только уникальные концерты)
    customer_concerts: str = Field(description="Список уникальных концертов покупателя через запятую")
    customer_concerts_count: int = Field(description="Количество уникальных концертов покупателя")
    
    # Связь с маршрутом
    best_route_id: Optional[int] = Field(default=None, foreign_key="route.id", description="ID лучшего маршрута")
    match_percentage: Optional[float] = Field(default=None, description="Процент совпадения")
    
    # Метаданные
    total_routes_checked: Optional[int] = Field(default=None, description="Количество проверенных маршрутов")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Дата создания записи")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Дата обновления записи") 