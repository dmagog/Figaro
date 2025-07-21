from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from models.route import Route
from models.composition import Author, Composition
from models.artist import Artist
from models.concert import Concert
from models.hall import Hall
from models.user import User

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
    # 1. Получаем все маршруты
    routes = session.exec(select(Route)).all()
    # TODO: join с концертами, артистами, композиторами для фильтрации

    # 2. Фильтрация по max_concerts
    filtered = [r for r in routes if getattr(r, 'Concerts', 0) <= int(preferences.get('max_concerts', 5))]

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