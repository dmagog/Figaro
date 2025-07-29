def get_all_halls_and_genres_with_visit_status(session, user_external_id: str, concerts_data: list) -> dict:
    """
    Получает все залы и жанры с отметкой о посещении пользователем
    
    Args:
        session: Сессия базы данных
        user_external_id: Внешний ID пользователя
        concerts_data: Список концертов пользователя
        
    Returns:
        Словарь с залами и жанрами и их статусом посещения
    """
    from collections import Counter
    
    # Получаем все уникальные жанры и залы из концертов пользователя
    all_genres = set()
    all_halls = set()
    
    # Собираем уникальные жанры и залы из концертов пользователя
    for concert_data in concerts_data:
        concert = concert_data['concert']
        
        # Добавляем жанр
        if concert.get('genre'):
            all_genres.add(concert['genre'])
        
        # Добавляем зал
        if concert.get('hall') and concert['hall'].get('name'):
            all_halls.add(concert['hall']['name'])
    
    # Преобразуем в списки
    all_genres = list(all_genres)
    all_halls = list(all_halls)
    
    # Счетчики посещений залов и жанров
    halls_counter = Counter()
    genres_counter = Counter()
    
    # Обрабатываем концерты пользователя
    for concert_data in concerts_data:
        concert = concert_data['concert']
        
        # Добавляем зал в счетчик
        if concert.get('hall') and concert['hall'].get('name'):
            halls_counter[concert['hall']['name']] += 1
        
        # Добавляем жанр в счетчик
        if concert.get('genre'):
            genres_counter[concert['genre']] += 1
    
    # Формируем список всех залов с количеством посещений
    halls_with_status = []
    for hall_name in all_halls:
        visit_count = halls_counter.get(hall_name, 0)
        halls_with_status.append({
            "name": hall_name,
            "visit_count": visit_count,
            "is_visited": visit_count > 0,
            "address": "",  # Адрес не доступен из данных концертов
            "seats": 0      # Количество мест не доступно из данных концертов
        })
    
    # Сортируем залы по убыванию количества посещений
    halls_with_status.sort(key=lambda x: x['visit_count'], reverse=True)
    
    # Формируем список всех жанров с количеством посещений
    genres_with_status = []
    for genre in all_genres:
        visit_count = genres_counter.get(genre, 0)
        genres_with_status.append({
            "name": genre,
            "visit_count": visit_count,
            "is_visited": visit_count > 0
        })
    
    # Сортируем жанры по убыванию количества посещений
    genres_with_status.sort(key=lambda x: x['visit_count'], reverse=True)
    
    return {
        "halls": halls_with_status,
        "genres": genres_with_status
    } 