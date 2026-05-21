"""Кэш доступных дневных маршрутов (этап 5). In-process для MVP; цель — Redis (ADR/05).

Инвалидация по событию изменения наличия (AvailabilityChanged)."""
from __future__ import annotations

from typing import Any, Dict, Optional

_store: Dict[int, Any] = {}


def get(festival_id: int) -> Optional[Any]:
    return _store.get(festival_id)


def set(festival_id: int, value: Any) -> None:
    _store[festival_id] = value


def invalidate(festival_id: int) -> None:
    _store.pop(festival_id, None)


def clear() -> None:
    _store.clear()
