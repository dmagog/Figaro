# 02 — Доменная модель и схема БД

Принципы схемы v3:
- **Единый внутренний `id` — `BIGINT GENERATED ALWAYS AS IDENTITY`** (решено: BIGINT, не UUID — данных немного, проще индексы/джойны/читаемость; UUID не нужен, внешнего распределённого генератора нет). Внешние ключи источников — отдельные поля, только для сопоставления при импорте. Никакого смешения ID-пространств (урок v2).
- **Внешних ключей может быть несколько, с разной семантикой — их не схлопываем.** У концерта это `show_num` (порядковый номер **внутри фестиваля**, ключ связи Excel-файлов и `Sostav`) и `crm_show_id` (идентификатор концерта в каталоге внешней CRM, где идут продажи). Это разные сущности по смыслу: первый — локальная нумерация фестиваля, второй — глобальный id в CRM.
- **Реальные FK и связи**, включён референсный контроль. M2M через явные link-таблицы.
- **Никаких денормализованных строк-ключей** (`"1,2,3"`). Состав маршрута — через таблицу связи.
- **Наличие — состояние, а не таблица-клон.** Нет `AvailableRoute`-дубля; «доступность» вычисляется/кэшируется поверх состояния концертов.
- **Деньги — `INTEGER`, в копейках** (целое, без float). Поле `price_kopecks`. Единая единица по всей системе.
- **Время — `timestamptz` (UTC в хранении).** «Сейчас» — из `FestivalClock` (раздел 04), tz-aware; фестиваль локальный (Europe/Moscow) — таймзона фестиваля в конфиге, отображение в ней, хранение в UTC. Длительности — `interval`.

## Сущности

### Фестиваль и скоупинг

Хранение — **одна БД, скоуп по фестивалю** ([ADR 0007](adr/0007-single-db-festival-scoping.md)). Каждый год фестиваля — отдельный набор данных в общей БД; ровно один фестиваль «активен» для публичного сайта.

**Festival** — фестиваль (корневая сущность)
- `id`, `name`, `year` (int), `sales_start_on` (date, старт продаж), `starts_on`/`ends_on` (date), `timezone` (str, напр. `Europe/Moscow`), `status` (enum: `draft`/`active`/`archived`), `created_at`
- `sales_start_on`/`starts_on`/`ends_on` задают границы фаз `pre_sale`/`on_sale`/`festival`/`post` ([04](04-simulation-and-availability.md#фазы-фестиваля)).
- Инвариант: не более одного `active` одновременно (частичный unique-индекс по `status = 'active'`).

**Скоуп.** Все данные конкретного фестиваля несут `festival_id` → Festival: каталог (Hall, HallTransition, Concert, Artist, Author, Composition, Genre, Program, FestivalDay, OffProgram), наличие (ConcertAvailability, AvailabilitySnapshot), маршруты (DayRoute, DayRouteConcert, Archetype), покупки (Purchase), а также пользовательские артефакты, привязанные к фестивалю (RouteSheet, UserPreferences). Запросы фильтруются по активному/выбранному `festival_id` в общем слое доступа (не «руками» в каждом месте).

**Глобальные (вне скоупа):** `User` (аккаунт один на все годы), `OutboxMessage` (при необходимости несёт `festival_id` в `payload`).

**Уникальность в скоупе:** `show_num` — unique `(festival_id, show_num)`; `Genre.name`, `FestivalDay.date` — unique в паре с `festival_id`. `crm_show_id` — **глобальный** (CRM сквозная между годами), уникальность по нему не навязываем (один CRM-концерт может встречаться в разные годы).

**Кросс-фестивальная идентичность** (тот же артист/автор в разные годы) — задача аналитики, отложена; в MVP каждая запись каталога принадлежит своему фестивалю.

### Каталог фестиваля (импортируется, меняется редко)

**Hall** — площадка
- `id`, `external_id`, `name`, `address`, `lat`, `lon`, `seats` (вместимость)

**HallTransition** — время перехода между залами
- `id`, `from_hall_id` → Hall, `to_hall_id` → Hall, `minutes` (int)
- Хранить **обе** направленности явно (в v2 хранили одну и достраивали обратную, полагаясь на симметрию). Если симметрично — заполняем обе при импорте.
- Уникальный индекс `(from_hall_id, to_hall_id)`.

**Concert** — концерт
- `id` (внутренний PK), `festival_id` → Festival, `show_num` (int, порядковый № **внутри фестиваля**; unique `(festival_id, show_num)`; ключ связи `ConcertList`/`ArtistDetails`/`show_details`/`Sostav`), `crm_show_id` (int, id концерта в каталоге внешней CRM; по нему привязываются покупки и обновления наличия), `title`
- `hall_id` → Hall
- `starts_at` (timestamptz), `duration` (interval), `ends_at` (генерируемое: `starts_at + duration`)
- `festival_day_id` → FestivalDay (денормализация дня для быстрых выборок)
- `price_kopecks` (int), `is_family_friendly` (bool)
- `capacity` (int) — вместимость **на концерт** (база для наличия и эмуляции). При импорте из выгрузки; если нет — дефолт `Hall.seats`. Используется в формулах наличия ([04](04-simulation-and-availability.md#модель-наличия-билетов)).
- `program_id` → Program (nullable) — см. ниже, для детекта повторов
- M2M: `artists` (ConcertArtist), `compositions` (ConcertComposition), `genres` (ConcertGenre)
- **Наличие**: см. отдельную таблицу `ConcertAvailability` ниже (не поле, чтобы хранить историю/таймлайн).

**FestivalDay** — день фестиваля
- `id`, `festival_id` → Festival, `date` (date; unique `(festival_id, date)`), `first_concert_at`, `last_concert_at`, `last_concert_ends_at` (агрегаты)
- `phase`-независим; вычисляется из концертов.

**Artist** — исполнитель
- `id`, `external_id`, `name`, `is_special` (bool — хедлайнер/особый)

**Author** — композитор/автор
- `id`, `external_id`, `name`

**Composition** — произведение
- `id`, `external_id`, `title`, `author_id` → Author

**Genre**
- `id`, `festival_id` → Festival, `name` (unique `(festival_id, name)`), `description`

**Program** — программа концерта (НОВОЕ, для детекта повторов)
- `id`, `signature` (хеш/нормализованный состав произведений+авторов)
- Концерты с одинаковой `program_id`/`signature` считаются «повтором программы».
- При импорте: программа = упорядоченное множество (произведение, автор); одинаковые наборы → одна `Program`.

**Link-таблицы:** `ConcertArtist(concert_id, artist_id)`, `ConcertComposition(concert_id, composition_id)`, `ConcertGenre(concert_id, genre_id)` — составные PK.

**OffProgram** — внепрограммные события
- `id`, `external_id`, `title`, `description`, `starts_at` (timestamptz), `duration` (interval), `hall_id` → Hall (а не строка, как в v2), `format` (enum), `is_recommended` (bool), `link`

### Наличие билетов (динамическое, во времени)

**ConcertAvailability** — текущее состояние наличия
- `concert_id` → Concert (PK)
- `is_on_sale` (bool), `tickets_left` (int, nullable), `updated_at` (timestamptz, по FestivalClock)
- `source` (enum: `crm_import` / `sim_curve` / `sim_replay`) — откуда взято значение

**AvailabilitySnapshot** (опционально, для аналитики «как продавалось») — история
- `id`, `concert_id` → Concert, `at` (timestamptz, по FestivalClock), `tickets_left`, `is_on_sale`, `source`
- Пишется при импорте/тиках эмуляции; питает реплей и пост-фактум графики.

> Маршруты ссылаются на концерты; «доступность маршрута» = все его концерты `is_on_sale`. Не храним отдельный клон-таблицей.

### Маршруты (предрасчёт + признаки)

**DayRoute** — дневной маршрут (предрасчитан, см. [03](03-route-engine.md))
- `id`, `festival_day_id` → FestivalDay
- Состав — через `DayRouteConcert(day_route_id, concert_id, position)` (а не строка `Sostav`)
- Денормализованные агрегаты для быстрого ранжирования: `concerts_count`, `halls_count`, `show_minutes`, `transition_minutes`, `wait_minutes`, `cost_kopecks`, `hall_changes`
- Признаки (числа): `comfort_score`, `diversity_score`, `depth_score`, `intellect_score`, `rare_authors_share`, `recommended_ratio`, … (набор из v2, уже посчитанный) + квантиль-нормированные версии
- `archetype_id` → Archetype (кластер; в v2 — `GMM_Cluster`)

**Archetype** — характер маршрута
- `id`, `key` (`marathon`/`comfort`/`explorer`/`deep`), `title`, `description`

> **Фестивальные маршруты (комбинации дней) НЕ материализуются.** Это декартово произведение дневных (десятки триллионов). Собираются лениво (top-k), см. [03](03-route-engine.md). Признаки фестивального маршрута = агрегация дневных (аддитивные — сумма; разнообразие — пересчёт по объединению).

### Пользователь и его данные

**User**
- `id`, `email` (unique!), `email_verified` (bool), `name`, `hashed_password`, `role` (enum: `user`/`researcher`/`admin`), `is_active`, `created_at`, `updated_at`
- `consent_at` (timestamptz, nullable) — согласие на обработку ПДн; `marketing_consent` (bool) — отдельное согласие на рассылки ([08](08-cross-cutting.md#приватность-и-персональные-данные-152-фз))
- (на будущее) `telegram_id`, `telegram_username` — для зоны роста с ботом

**UserPreferences** — ответы анкеты (структурировано, не свободный JSON)
- PK `(user_id → User, festival_id → Festival)` — анкета привязана к конкретному фестивалю (дни/жанры/авторы фестиваль-специфичны)
- `pace` (enum), `available_days` (int[]/jsonb), `time_windows` (jsonb), `interest_vector` (enum new↔deep), `favorite_author_ids` (int[]), `favorite_genre_ids` (int[]), `updated_at`
- Хранить структурно, чтобы движок не парсил произвольный dict (урок v2).

**RouteSheet** — личный маршрутный лист (НОВОЕ, персистентное)
- `id`, `user_id` → User, `festival_id` → Festival, `title`, `created_at`, `updated_at`, `source` (`from_archetype`/`manual`/`split_from_purchases`)
- Несколько листов на пользователя **в рамках фестиваля** (нужно для разложения по людям).

**RouteSheetItem** — концерт в листе
- `id`, `route_sheet_id` → RouteSheet, `concert_id` → Concert, `is_pinned` (bool), `added_at`
- Уникальность `(route_sheet_id, concert_id)`.

### CRM / покупки (импорт)

**Purchase** — историческая покупка (из CRM-выгрузки)
- `id`, `external_op_id` (= OpId), `customer_external_id` (str, = ClientId — псевдоним, не ФИО; см. [приватность](08-cross-cutting.md#приватность-и-персональные-данные-152-фз)), `concert_id` → Concert (привязка по `crm_show_id`: в выгрузке CRM концерт идентифицируется `ShowId`), `purchased_at` (timestamptz), `price_kopecks` (int)
- Используется для: реплея наличия (раздел 04), будущей персонализации, разложения по людям.

**Customer** — агрегат по `customer_external_id` (может быть VIEW, не таблица): сумма покупок, уникальные концерты, дни.

### Уведомления (outbox)

**OutboxMessage** — событие к доставке (см. [05](05-architecture-and-platform.md#уведомления-outbox))
- `id`, `type` (enum: `concert_reminder`/`availability_alert`), `payload` (jsonb), `user_id` → User, `scheduled_for` (timestamptz, по FestivalClock), `status` (enum: `pending`/`sent`/`failed`), `attempts` (int), `idempotency_key` (str, **unique**), `created_at`, `sent_at`
- `idempotency_key` детерминирован по смыслу события → повторная постановка не плодит дублей (`ON CONFLICT DO NOTHING`).

## Доменные события

Чтобы не «руками» рассыпать побочные эффекты по коду, ключевые изменения публикуют событие, на которое подписаны обработчики:

- **`AvailabilityChanged(concert_id, is_on_sale, tickets_left, at)`** — публикуется при изменении наличия (тик эмуляции или CRM-импорт). Подписчики: инвалидация разделяемого кэша «доступных дневных маршрутов» ([03](03-route-engine.md#наличие-как-фильтр)); постановка `availability_alert` для листов, где концерт распродан; запись `AvailabilitySnapshot`.

Событие — внутридоменное (не брокер); реализация в MVP — синхронные обработчики. Это та же точка, которую при росте можно вынести на брокер без изменения издателя.

## Индексы (горячие пути)

Минимальный набор под частые выборки (детали — при реализации). Почти все горячие выборки фильтруются по `festival_id` — он входит в составные индексы:
- `Festival` — частичный unique по `status` где `status = 'active'` (не более одного активного).
- `Concert(festival_id, show_num)` unique; `Concert(festival_id, starts_at)`, `Concert(festival_day_id)`, `Concert(hall_id)`, `Concert(program_id)`, `Concert(crm_show_id)`.
- `HallTransition(from_hall_id, to_hall_id)` — unique; обе направленности.
- `DayRoute(festival_day_id)`, `DayRoute(archetype_id)`; `DayRouteConcert(day_route_id)`, `DayRouteConcert(concert_id)`.
- `ConcertAvailability(is_on_sale)` (частичный по `is_on_sale = true`), `AvailabilitySnapshot(concert_id, at)`.
- `Purchase(customer_external_id)`, `Purchase(concert_id)`, `Purchase(purchased_at)`.
- `RouteSheet(user_id)`; `RouteSheetItem(route_sheet_id, concert_id)` — unique.
- `OutboxMessage(idempotency_key)` — unique; `OutboxMessage(status, scheduled_for)` — для выборки диспетчером.
- `User(email)` — unique.

## Изменения относительно v2 (сводно)

| v2 | v3 |
|----|----|
| `Route.Sostav = "1,2,3"` (external_id) | `DayRouteConcert` (FK на внутренний id) + позиция |
| `AvailableRoute` — копия 45 колонок | наличие = состояние концертов + кэш |
| `tickets_left` на Concert, затирается рандомом | `ConcertAvailability` + история `AvailabilitySnapshot` |
| `User.preferences` — свободный JSON | `UserPreferences` со схемой |
| маршрутный лист — пересборка из Purchase | `RouteSheet` + `RouteSheetItem` (персистентно) |
| роль — строка-косметика | `role` enum + реальный RBAC |
| `OffProgram.hall_name` строка | `hall_id` FK |
| повтор программы не детектируется | `Program.signature` |
| смешение `ShowNum`/`ShowId` | `show_num` (в фестивале) и `crm_show_id` (CRM) — раздельно, оба на внутренний `id` |
| данные «одного фестиваля» в общей БД без явной модели | `Festival` + `festival_id`-скоуп; один активный; админ «Создать фестиваль» |

## Замечания по миграции данных

- Импорт из текущих Excel/CSV возможен: маппинг `external_id` → новый `id`. Признаки маршрутов и GMM-кластеры переносятся как есть в `DayRoute`/`Archetype`. Реальные файлы и колонки источников → сущности — в [05](05-architecture-and-platform.md#источники-данных-реальные-файлы).
- Историю покупок (`GoodOperations.xlsx`) переносим в `Purchase` — она же база для реплея наличия (с оговоркой о качестве дат покупок, см. [05](05-architecture-and-platform.md#источники-данных-реальные-файлы)).
