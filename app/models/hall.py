from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    pass  # Для избежания циклических импортов


class Hall(SQLModel, table=True, extend_existing=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Название зала")
    concert_count: int = Field(description="Количество концертов в зале")
    address: Optional[str] = Field(default=None, description="Адрес зала")
    latitude: Optional[float] = Field(default=None, description="Широта (latitude)")
    longitude: Optional[float] = Field(default=None, description="Долгота (longitude)")
    seats: int = Field(default=0, description="Количество мест в зале")
    
    # Связи с переходами между залами
    outgoing_transitions: List["HallTransition"] = Relationship(
        back_populates="from_hall",
        sa_relationship_kwargs={"foreign_keys": "HallTransition.from_hall_id"}
    )
    incoming_transitions: List["HallTransition"] = Relationship(
        back_populates="to_hall",
        sa_relationship_kwargs={"foreign_keys": "HallTransition.to_hall_id"}
    )


class HallTransition(SQLModel, table=True, extend_existing=True):
    """Модель для хранения времени переходов между залами"""
    
    __tablename__ = "hall_transition"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Связи с залами
    from_hall_id: int = Field(foreign_key="hall.id", description="ID зала отправления")
    to_hall_id: int = Field(foreign_key="hall.id", description="ID зала назначения")
    
    # Время перехода в минутах
    transition_time: int = Field(description="Время перехода в минутах")
    
    # Связи с моделью Hall
    from_hall: Optional[Hall] = Relationship(
        back_populates="outgoing_transitions",
        sa_relationship_kwargs={"foreign_keys": "HallTransition.from_hall_id"}
    )
    to_hall: Optional[Hall] = Relationship(
        back_populates="incoming_transitions",
        sa_relationship_kwargs={"foreign_keys": "HallTransition.to_hall_id"}
    )
    
    class Config:
        schema_extra = {
            "example": {
                "from_hall_id": 1,
                "to_hall_id": 2,
                "transition_time": 11
            }
        }
