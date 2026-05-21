# Changelog

Версионирование итеративное; мажор = **3** (третья итерация сервиса). Минор растёт с каждым завершённым этапом [дорожной карты](docs/06-mvp-roadmap.md).

## [3.5.0] — Этап 5: наличие и эмуляция
- Модели `AvailabilitySnapshot` (история), `SimState` (режим/seed эмуляции).
- `services/availability.py`: движок `sim_curve` (детерминир. кривая+seed, популярные раньше) и `sim_replay` (по `purchased_at`); `recompute` пишет состояние + снимок; `reset_to_sales_start`; `tick(clock)`; фильтры `route_available`/`available_day_routes`; пульт (`set_mode`).
- `services/cache.py`: кэш доступных маршрутов + инвалидация (AvailabilityChanged).
- Замыкание «шва наличия»: `recommend()` отсеивает распроданные маршруты.
- BDD: зелёная `availability` (кривая/реплей/ускоренный тик+кэш/история/фильтр/пульт). Тесты: pytest 45/45, behave 102 сценария (12 фич).

## [3.4.0] — Этап 4: подбор и маршрутный лист
- `ConcertAvailability` (состояние наличия) + `services/availability.py` (is_on_sale/seam, альтернатива). Полный движок curve/replay — этап 5.
- `services/sheets.py`: создание листа (из маршрута / с нуля), добавление с проверками (наличие→reject+альтернатива, накладка→overlap, флаг повтора программы, статус перехода с соседом), удаление, закрепление, подсказки дополнения.
- `services/recommend.py`: подбор по архетипам над `DayRoute` (нормированный скор comfort/diversity + бонус за любимое), карточки, релаксация по числу концертов.
- BDD: зелёные `recommendations`, `route_sheet`, `suggestions`. Тесты: pytest 40/40, behave 91 сценарий (11 фич).

## [3.3.0] — Этап 3: аккаунты, безопасность, анкета
- Модели `User`, `UserPreferences`, `AuthToken`, `UserSession`, `RouteSheet`, `RouteSheetItem`.
- `services/auth.py`: pbkdf2-хеши, регистрация (с согласием на ПДн), верификация email, вход с lockout, сброс пароля по токену с TTL, сессии (выход/истечение), RBAC `can_access`, смена роли (admin), CSRF, проверка владения листом, удаление аккаунта; псевдонимизированная аналитика.
- `services/recommend.py`: анкета → веса (темп → число концертов/комфорт, вектор интереса → разнообразие/глубина, любимые авторы → бонус), жёсткий фильтр по дням/окнам.
- BDD: зелёные `auth_roles`, `security`, `questionnaire`. Тесты: pytest 36/36, behave 70 сценариев.

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
