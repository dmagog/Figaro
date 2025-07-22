from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from models.route import Route
from models.composition import Author, Composition
from models.artist import Artist
from models.concert import Concert
from models.hall import Hall
from models.user import User
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

# --- Основная функция рекомендаций ---
def get_recommendations(
    session: Session,
    preferences: dict,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Возвращает подборки маршрутов по анкете пользователя.
    preferences: dict (priority, max_concerts, diversity, composers, artists, planned_concerts)
    """
    logger.info(f"Получение рекомендаций с предпочтениями: {preferences}")
    
    # 1. Получаем все маршруты
    routes = session.exec(select(Route)).all()
    logger.info(f"Найдено маршрутов в базе: {len(routes)}")
    
    if not routes:
        logger.warning("В базе данных нет маршрутов")
        return {
            "top_weighted": [],
            "top_intellect": [],
            "top_comfort": [],
            "top_balanced": [],
            "alternatives": []
        }
    
    # 2. Фильтрация по количеству концертов (min_concerts/max_concerts) с понижением min_concerts
    min_concerts = preferences.get('min_concerts')
    max_concerts = preferences.get('max_concerts')
    logger.info(f"Фильтрация по min_concerts: {min_concerts}, max_concerts: {max_concerts}")
    filtered = []
    if min_concerts is not None and max_concerts is not None:
        cur_min = min_concerts
        while cur_min >= 0:
            filtered = [r for r in routes if cur_min <= getattr(r, 'Concerts', 0) <= max_concerts]
            logger.info(f"min_concerts={cur_min}, найдено маршрутов: {len(filtered)}")
            if filtered:
                break
            cur_min -= 1
        if cur_min < 0:
            filtered = [r for r in routes if getattr(r, 'Concerts', 0) <= max_concerts]
    elif min_concerts is not None:
        cur_min = min_concerts
        while cur_min >= 0:
            filtered = [r for r in routes if getattr(r, 'Concerts', 0) >= cur_min]
            logger.info(f"min_concerts={cur_min}, найдено маршрутов: {len(filtered)}")
            if filtered:
                break
            cur_min -= 1
        if cur_min < 0:
            filtered = routes
    elif max_concerts is not None:
        filtered = [r for r in routes if getattr(r, 'Concerts', 0) <= max_concerts]
    else:
        filtered = routes  # Без ограничений
    logger.info(f"После фильтрации по количеству концертов: {len(filtered)} маршрутов")

    # 3. Фильтрация по diversity (уникальные композиторы и доля главного)
    # TODO: реализовать через связи

    # 4. Фильтрация по include/exclude (composers, artists, concerts)
    # TODO: реализовать через связи

    # 5. Взвешенное ранжирование (score не добавляем в объект, а считаем отдельно)
    weights = {
        "intellect": (1.0, 0.0),
        "comfort": (0.0, 1.0),
        "balance": (0.5, 0.5)
    }
    w_i, w_c = weights.get(preferences.get('priority', 'balance'), (0.5, 0.5))
    logger.info(f"Веса для ранжирования: intellect={w_i}, comfort={w_c}")
    
    weighted_routes = [
        (r, w_i * getattr(r, 'IntellectScore', 0) + w_c * getattr(r, 'ComfortScore', 0))
        for r in filtered
    ]

    # 6. Сортировка и подборки
    top_weighted = [route_to_dict(r, score) for r, score in sorted(weighted_routes, key=lambda x: x[1], reverse=True)[:top_n]]
    top_intellect = [route_to_dict(r) for r in sorted(filtered, key=lambda r: getattr(r, 'IntellectScore', 0), reverse=True)[:top_n]]
    top_comfort = [route_to_dict(r) for r in sorted(filtered, key=lambda r: getattr(r, 'ComfortScore', 0), reverse=True)[:top_n]]
    top_balanced = [route_to_dict(r) for r in sorted(filtered, key=lambda r: abs(getattr(r, 'IntellectScore', 0) - getattr(r, 'ComfortScore', 0)))[:top_n]]

    # 7. Альтернативы (по planned_concerts)
    # TODO: реализовать Jaccard-поиск альтернатив
    alternatives = []

    logger.info(f"Результат: top_weighted={len(top_weighted)}, top_intellect={len(top_intellect)}, top_comfort={len(top_comfort)}, top_balanced={len(top_balanced)}")

    # 8. Формируем результат
    return {
        "top_weighted": top_weighted,
        "top_intellect": top_intellect,
        "top_comfort": top_comfort,
        "top_balanced": top_balanced,
        "alternatives": alternatives
    }


def route_to_dict(route: Route, weighted_score: Optional[float] = None) -> dict:
    """Преобразует маршрут в словарь для фронта (состав, баллы, пояснения)"""
    return {
        "id": route.id,
        "concerts": route.Sostav if hasattr(route, 'Sostav') else [],
        "concerts_count": getattr(route, 'Concerts', 0),
        "intellect": getattr(route, 'IntellectScore', 0),
        "comfort": getattr(route, 'ComfortScore', 0),
        "weighted": weighted_score if weighted_score is not None else None,
        "trans_time": getattr(route, 'TransTime', 0),
        "wait_time": getattr(route, 'WaitTime', 0),
        "costs": getattr(route, 'Costs', 0),
        # TODO: добавить пояснения, состав, артистов, композиторов
    } 