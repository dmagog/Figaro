# Changelog

Версионирование итеративное; мажор = **3** (третья итерация сервиса). Минор растёт с каждым завершённым этапом [дорожной карты](docs/06-mvp-roadmap.md).

## [3.1.0] — Этап 1: доменная схема, фестиваль и импорт каталога
- `Festival` + скоуп `festival_id` по всем сущностям каталога; «один активный» (инвариант).
- Доменные модели (SQLModel): Hall, HallTransition, Concert, Artist, Author, Composition, Genre, Program, FestivalDay, OffProgram, Purchase + link-таблицы.
- Создание фестиваля (`draft`) и импорт каталога в рамках фестиваля: связка по `show_num`, покупки по `crm_show_id`, capacity (выгрузка→зал), сигнатуры программ, переходы в обе стороны, дни фестиваля, идемпотентность, устойчивый парсинг дат.
- BDD: зелёные `festival_lifecycle` (этап 1) и `catalog_import`.

## [3.0.0] — Этап 0: каркас
- Структура проекта (FastAPI+HTMX/Postgres, планировщик без брокера), config, docker-compose.
- Полная спецификация v3 (`docs/`) + 7 ADR + 95 BDD-сценариев (`features/`).
- `FestivalClock` (real/offset/accelerated) + фазы; `clock.feature` 10/10, pytest зелёные.
