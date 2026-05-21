"""Устойчивый парсинг дат из выгрузок.

В дампе v2 встречалась эпоха 1970 — артефакт конвертации форматов колонок
(см. docs/05). Здесь распознаём datetime / ISO-строку / Excel-serial и
отбраковываем заведомо некорректные (год < 2000 для фестиваля 2022+).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

_EXCEL_EPOCH = datetime(1899, 12, 30)
_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d",
            "%d.%m.%Y %H:%M:%S", "%d.%m.%Y")


def parse_datetime(value) -> datetime:
    if value is None or value == "":
        raise ValueError("пустая дата")
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, (int, float)):
        dt = _EXCEL_EPOCH + timedelta(days=float(value))
    else:
        s = str(value).strip()
        dt = None
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            for fmt in _FORMATS:
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            raise ValueError(f"не распознан формат даты: {value!r}")
    if dt.year < 2000:
        raise ValueError(f"подозрительная дата (артефакт конвертации?): {dt.isoformat()}")
    return dt
