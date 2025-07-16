# Исправление дублирования инициализации AvailableRoute

## Проблема

При загрузке маршрутов из CSV файла происходила двойная инициализация AvailableRoute:

1. **Первый раз**: `ensure_available_routes_exist()` вызывался из `load_routes_from_csv()`
2. **Второй раз**: `init_available_routes()` вызывался повторно в конце `load_routes_from_csv()`

Это приводило к:
- Двойной обработке всех 37,946 маршрутов
- Увеличению времени загрузки в 2 раза
- Избыточной нагрузке на базу данных
- Дублированию логов

## Причина

### В `data_loader.py`:
```python
# Проблемный код:
route_service.ensure_available_routes_exist(session)  # Первый вызов
route_service.init_available_routes_cache(session)    # Мог вызвать повторную инициализацию
```

### В `route_service.py`:
```python
# Проблема в get_cached_available_routes_count():
def get_cached_available_routes_count(session: Session) -> int:
    stats_record = session.exec(select(Statistics).where(Statistics.key == "available_routes_count")).first()
    if stats_record:
        return stats_record.value
    else:
        # Если кэша нет, подсчитываем и создаём
        available_count = len(session.exec(select(AvailableRoute)).all())
        update_available_routes_cache(session, available_count)
        return available_count
```

Кэш мог быть пустым, даже когда AvailableRoute уже существовали в базе.

## Решение

### 1. Улучшена функция `ensure_available_routes_exist()`

```python
def ensure_available_routes_exist(session: Session, status_dict: Dict = None) -> bool:
    try:
        # Сначала проверяем кэш
        existing_count = get_cached_available_routes_count(session)
        
        if existing_count == 0:
            # Если кэш показывает 0, проверяем реальное количество в базе
            actual_count = len(session.exec(select(AvailableRoute)).all())
            
            if actual_count == 0:
                # Действительно нет AvailableRoute - инициализируем
                result = init_available_routes(session, status_dict=status_dict)
                return True
            else:
                # AvailableRoute есть, но кэш пустой - обновляем кэш
                update_available_routes_cache(session, actual_count)
                return False
        else:
            return False
```

### 2. Добавлена защита в `init_available_routes()`

```python
def init_available_routes(session: Session, status_dict: Dict = None) -> Dict[str, int]:
    # Проверяем, есть ли уже AvailableRoute
    existing_count = len(session.exec(select(AvailableRoute)).all())
    if existing_count > 0:
        logger.info(f"AvailableRoute уже существуют ({existing_count} записей), пропускаем инициализацию")
        return {
            'total_routes': len(session.exec(select(Route)).all()),
            'available_routes': existing_count,
            'unavailable_routes': 0
        }
```

### 3. Оптимизирован вызов в `load_routes_from_csv()`

```python
# Проверяем и инициализируем AvailableRoute (если нужно)
was_initialized = route_service.ensure_available_routes_exist(session)

# Инициализируем кэши только если AvailableRoute не были созданы заново
if not was_initialized:
    route_service.init_available_routes_cache(session)
    route_service.init_available_concerts_cache(session)
```

## Результат

### До исправления:
```
INFO:services.crud.route_service:Найдено 37946 маршрутов для проверки
INFO:services.crud.route_service:Проверено 37946/37946 маршрутов (100.0%) - найдено доступных: 37946
INFO:services.crud.route_service:Инициализация завершена: 37946 доступных, 0 недоступных из 37946 маршрутов
INFO:services.crud.route_service:Найдено 37946 маршрутов для проверки
INFO:services.crud.route_service:Проверено 37946/37946 маршрутов (100.0%) - найдено доступных: 37946
INFO:services.crud.route_service:Инициализация завершена: 37946 доступных, 0 недоступных из 37946 маршрутов
```

### После исправления:
```
INFO:services.crud.route_service:Найдено 37946 маршрутов для проверки
INFO:services.crud.route_service:Проверено 37946/37946 маршрутов (100.0%) - найдено доступных: 37946
INFO:services.crud.route_service:Инициализация завершена: 37946 доступных, 0 недоступных из 37946 маршрутов
INFO:services.crud.route_service:Найдено 37946 AvailableRoute в кэше, инициализация не требуется
```

## Тестирование

Создан тестовый скрипт `test_route_duplication.py` для проверки:

```bash
cd app
python test_route_duplication.py
```

Скрипт проверяет:
- Отсутствие дублирования инициализации
- Консистентность данных между попытками
- Производительность (вторая попытка должна быть быстрее)

## Преимущества

1. **Производительность**: Сокращение времени загрузки в 2 раза
2. **Надежность**: Защита от дублирования операций
3. **Консистентность**: Правильная работа кэша
4. **Мониторинг**: Четкие логи без дублирования

## Заключение

Проблема дублирования инициализации AvailableRoute полностью решена. Система теперь работает эффективно и предсказуемо, избегая избыточных операций при загрузке маршрутов. 