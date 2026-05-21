# Changelog

Версионирование итеративное; мажор = **3** (третья итерация сервиса). Минор растёт с каждым завершённым этапом [дорожной карты](docs/06-mvp-roadmap.md).

## [3.2.0] — Этап 2: движок маршрутов
- Конфликты переходов (`routing/conflicts.py`): статусы ok/tight/hurry/overlap/same_hall/same_building/no_data, пороги из конфига, резолв walk (матрица → координатная оценка по `walk_speed` → no_data).
- Дневные маршруты: DAG достижимости → перечисление путей → агрегаты/признаки → Pareto-отсев; модели `DayRoute`/`DayRouteConcert`/`Archetype`.
- Фаза предрасчёта по ВСЕМ дням фестиваля (`batch/precompute.py`), идемпотентно по дню; гейт активации (нельзя `active` без предрасчёта).
- Ленивая сборка фестивальных маршрутов: top-k над произведением (куча), аддитивные признаки суммой, разнообразие по объединению.
- BDD: зелёные `transitions`, `route_engine` и отложенные ранее `@stage2`-активации `festival_lifecycle`. Тесты: pytest 25/25, behave 42 сценария.

## [3.1.0] — Этап 1: доменная схема, фестиваль и импорт каталога
- `Festival` + скоуп `festival_id` по всем сущностям каталога; «один активный» (инвариант).
- Доменные модели (SQLModel): Hall, HallTransition, Concert, Artist, Author, Composition, Genre, Program, FestivalDay, OffProgram, Purchase + link-таблицы.
- Создание фестиваля (`draft`) и импорт каталога в рамках фестиваля: связка по `show_num`, покупки по `crm_show_id`, capacity (выгрузка→зал), сигнатуры программ, переходы в обе стороны, дни фестиваля, идемпотентность, устойчивый парсинг дат.
- BDD: зелёные `festival_lifecycle` (этап 1) и `catalog_import`.

## [3.0.0] — Этап 0: каркас
- Структура проекта (FastAPI+HTMX/Postgres, планировщик без брокера), config, docker-compose.
- Полная спецификация v3 (`docs/`) + 7 ADR + 95 BDD-сценариев (`features/`).
- `FestivalClock` (real/offset/accelerated) + фазы; `clock.feature` 10/10, pytest зелёные.
