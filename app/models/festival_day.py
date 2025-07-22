from typing import Optional
from datetime import date, time
from sqlmodel import SQLModel, Field


class FestivalDay(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day: date = Field(index=True, description="Дата фестивального дня")
    first_concert_time: time = Field(description="Время начала первого концерта")
    last_concert_time: time = Field(description="Время начала последнего концерта")
    end_of_last_concert: time = Field(description="Время окончания последнего концерта")
    concert_count: int = Field(description="Количество концертов в этот день")
    available_concerts: int = Field(description="Количество концертов с доступными билетами")
