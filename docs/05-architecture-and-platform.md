# 05 — Архитектура и платформа

## Стек

- **Backend:** Python 3.11+, FastAPI.
- **Фронт:** server-rendered Jinja2 + **HTMX** (частичные обновления без SPA) + немного Alpine.js при необходимости. Tailwind/готовый CSS — на выбор.
- **БД:** PostgreSQL. ORM — SQLModel/SQLAlchemy 2.x (или чистый SQLAlchemy; SQLModel ок, но фиксируем версии, см. урок v2 про pydantic).
- **Миграции:** Alembic (в v2 не было — только drop/create).
- **Планировщик:** APScheduler — **один на инстанс** (отдельный процесс/сервис `scheduler` либо лидер через `pg_try_advisory_lock`), не в каждом uvicorn-воркере. Без брокера в MVP.
- **Брокеры (Celery/RabbitMQ):** НЕТ в MVP; вводятся вместе с ботом/массовыми рассылками.
- **Кэш:** разделяемый между воркерами (Redis) — нужен из-за инвалидации «доступных дневных маршрутов» при изменении наличия. В минимальной конфигурации `--workers 1` допустим in-process кэш, но архитектурно целимся в Redis.
- **Контейнеризация:** Docker Compose. Сервисы MVP: `app` (FastAPI), `scheduler` (тики/диспетчер), `db` (Postgres), опц. `redis`. Порты — нестандартные (диапазон 49xxx), чтобы не толкаться с другими проектами.

> Урок v2: `fastapi==0.104.1` оказался несовместим с подтянувшимся `pydantic 2.13`. В v3 **пинуем взаимосовместимые версии** (fastapi/starlette/pydantic) и держим lock-файл актуальным.

## Структура проекта (модульная, без дублирования каналов)

Главный урок v2 — логика дублировалась между `user.py` и `temp_routes.py` для web и telegram. В v3 **доменное ядро отделено от каналов**.

```
figaro/
├── domain/                 # чистая логика, без FastAPI/HTTP
│   ├── models.py           # SQLModel-сущности (раздел 02)
│   ├── routing/            # DAG, дневные маршруты, top-k, конфликты
│   │   ├── conflicts.py    # evaluate_transition (пороги из config)
│   │   ├── dayroutes.py    # предрасчёт дневных маршрутов
│   │   ├── combine.py      # ленивая top-k сборка по дням
│   │   └── suggest.py      # подсказки дополнения
│   ├── recommend.py        # анкета → веса → ранжирование
│   ├── availability/       # модели наличия (curve / replay / crm)
│   ├── clock.py            # FestivalClock + фазы
│   ├── notifications.py    # outbox: постановка событий
│   └── sheets.py           # операции над RouteSheet
├── services/               # прикладные сервисы (транзакции, кэш, оркестрация)
├── web/                    # FastAPI: роуты, зависимости, шаблоны HTMX
│   ├── deps.py             # auth, текущий пользователь, RBAC
│   ├── user_routes.py      # экраны зрителя
│   ├── admin_routes.py     # админка + пульт эмуляции
│   └── templates/
├── importing/              # импорт Excel/CRM (раздел ниже)
├── scheduler.py            # тики наличия/уведомлений (APScheduler)
├── config.py               # настройки (pydantic-settings), все пороги/ключи
├── migrations/             # Alembic
└── batch/                  # офлайн-предрасчёт дневных маршрутов и признаков
```

Каналы (web сейчас, bot потом) **только вызывают `domain`/`services`** — не реализуют логику у себя.

## Роли и доступ (RBAC)

- `role` — enum `user | researcher | admin` (реальный, не косметика как в v2).
- Единая зависимость FastAPI `require_role(*roles)` вместо ~50 inline-проверок `is_superuser`.
- Матрица доступа:

| Область | user | researcher | admin |
|---------|:----:|:----------:|:-----:|
| Анкета, маршрутный лист, подбор | ✅ | ✅ | ✅ |
| Дашборды/аналитика/маркетинг-фильтры | — | ✅ | ✅ |
| Пользователи, системные настройки | — | — | ✅ |
| Пульт эмуляции, запуск пересчётов, импорт | — | — | ✅ |

- Аутентификация: сессия или JWT в httponly-cookie (как в v2, но возвращаем объект пользователя с ролью, а не только email). Пароли — argon2/bcrypt.
- Управление ролями — через admin-UI (в v2 не было; роль ставилась только сидом/в БД).
- Детали безопасности (CSRF для HTMX, rate-limit, logout, сброс пароля, верификация email) и приватности/ПДн — в [08](08-cross-cutting.md).

## Экраны и эндпоинты (HTMX)

Инвентарь поверхности MVP. Полные страницы (`GET`, рендер шаблона) + частичные HTMX-эндпоинты (`hx-*`, возвращают фрагмент). Мутации требуют CSRF-токен ([08](08-cross-cutting.md#безопасность)).

| Экран / действие | Метод, путь | Роль | Тип |
|---|---|---|---|
| Лендинг / hero | `GET /` | все | страница |
| Регистрация / вход / logout | `GET,POST /auth/*` | гость | страница+форма |
| Сброс пароля, верификация email | `GET,POST /auth/reset`, `/auth/verify` | гость | форма |
| Анкета (4 шага) | `GET /onboarding`, `POST /onboarding/step/{n}` | user | частичные |
| Подбор (архетипы + top-k) | `GET /recommendations` | user | страница |
| Карточка маршрута | `GET /routes/{id}` | user | частичный |
| Маршрутный лист | `GET /sheets/{id}` | user (владелец) | страница |
| Добавить/убрать/закрепить концерт | `POST,DELETE /sheets/{id}/items` | user (владелец) | частичный |
| Подсказки «что добавить» | `GET /sheets/{id}/suggestions` | user (владелец) | частичный |
| Расписание с фильтрами | `GET /schedule` | user | страница+частичные |
| Управление фестивалями (создать/импорт/предрасчёт/активировать) | `GET,POST /admin/festivals`, `/admin/festivals/{id}/import`, `/precompute`, `/activate` | admin | страница+формы |
| Пульт эмуляции | `GET,POST /admin/simulation` | admin | страница+частичные |
| Импорт остатков / запуск пересчёта | `POST /admin/import/availability`, `/admin/recompute` | admin | форма |
| Управление пользователями / ролями | `GET,POST /admin/users` | admin | страница |
| Дашборды/аналитика | `GET /research/*` | researcher, admin | страница (зона роста) |

Проверка владения ресурсом (`sheets/{id}` принадлежит текущему пользователю) — в `web/deps.py`, не в шаблонах.

## Уведомления (outbox)

«Готово к брокеру, но без брокера»:
- Доменный код вызывает `notifications.enqueue(event)` — пишет строку в таблицу **`OutboxMessage`** (`id`, `type`, `payload`, `scheduled_for` (по FestivalClock), `status`, `attempts`, **`idempotency_key`** (unique)).
- **Идемпотентность.** `idempotency_key` детерминирован по смыслу события (например, `reminder:{user_id}:{concert_id}` или `alert:{sheet_id}:{concert_id}:soldout`). Повторная постановка того же события — `INSERT … ON CONFLICT DO NOTHING`, поэтому повторные/гонящиеся тики не плодят дублей писем.
- **Диспетчер** — один на инстанс (тот же single-runner, что и тики, см. [04](04-simulation-and-availability.md)). На каждом тике берёт `status=pending AND scheduled_for ≤ clock.now()` под `FOR UPDATE SKIP LOCKED`, отправляет (email через SMTP/провайдера), помечает `sent/failed`, ретраит с backoff и лимитом `attempts`.
- Точки вызова не знают про транспорт → позже подменяем диспетчер на Celery+broker без изменения доменного кода.
- Типы событий MVP: `concert_reminder` (за X до концерта по плану зрителя), `availability_alert` (концерт из листа распродан → предложить альтернативу). Генерация альтернативы в MVP — **простая** (ближайший по времени доступный концерт того же окна/жанра); «умная» альтернатива — `@growth`. В `accelerated` весь цикл проверяется за минуты.

## Жизненный цикл фестиваля

Хранение — один DB со скоупом по фестивалю ([ADR 0007](adr/0007-single-db-festival-scoping.md), [02](02-domain-model.md#фестиваль-и-скоупинг)). Подготовка фестиваля — **отдельный admin-конвейер**, гейтящийся перед публикацией:

1. **Создать** `Festival(status=draft)` — название, год, даты, таймзона.
2. **Импорт каталога** этого фестиваля (Excel/CRM) → концерты/залы/переходы/программы/артисты/дни (всё с `festival_id`).
3. **Предрасчёт** дневных маршрутов **по всем дням** фестиваля + признаки + архетипы ([03](03-route-engine.md#когда-и-для-каких-дней-считаем)).
4. **Ревью** админом: счётчики/качество (число концертов, маршрутов по дням, предупреждения импорта).
5. **Активация** → `status=active` (ровно один активный; предыдущий → `archived`). С этого момента фестиваль виден публике, идёт sync наличия.

**Активный фестиваль.** Публичный сайт работает с текущим `active`-фестивалём; слой доступа подставляет его `festival_id` во все запросы (зритель не выбирает год вручную в MVP). Админ может работать с `draft`-фестивалём в предпросмотре до активации. Переходы: `draft → active → archived`; архивный доступен аналитике (исследователь, зона роста), но не публичным операциям.

## Импорт данных и CRM

Импорт всегда **в рамках конкретного фестиваля** (`festival_id`). Разделяем **полный сидинг каталога** и **инкрементальное обновление**:

1. **Полный сидинг** (`importing/seed.py`): Excel-выгрузки → каталог фестиваля (Hall, HallTransition, Concert, Artist, Author, Composition, Genre, Program, OffProgram, FestivalDay) + Purchase, всё с `festival_id`. Идемпотентно по `(festival_id, внешний ключ)` (upsert), без drop/create таблиц (для этого Alembic). Никаких хардкод-путей внутри — пути из конфига; файл читается один раз.
2. **Предрасчёт маршрутов** (`batch/`): из подготовленного CSV (`RouteRange_with_GMM`) или собственного перечислителя → `DayRoute`/признаки/архетипы. Запускается админом по необходимости (форс-мажор).
3. **Обновление наличия** (`importing/availability.py`): периодический файл с остатками → `ConcertAvailability` (`source=crm_import`); позже — pull по CRM API с той же частотой. Инвалидация кэша маршрутов.

Маппинг ID: импорт ведёт `external_id → internal id`; внутри системы — только internal id.

### Источники данных (реальные файлы)

Структуры берём из существующих выгрузок (`app/data/*` в v2). Это контракт парсеров `importing/seed.py`; колонки → сущности [02](02-domain-model.md):

| Файл | Сущность v3 | Ключевые колонки |
|------|-------------|------------------|
| `ConcertList-good.xlsx` (100) | Concert | `ShowNum` (порядковый ключ связи), `ShowId` (внешний id), `ShowName`, `ShowDate` (datetime), `HallName`, `Genre`, `ShowLong` (длительность "ЧЧ:ММ:СС"), `Family`, `Price`, `Tickets` (bool), `link` |
| `HallList-good.xlsx` (9) | Hall | `HallName`, `count`, `Adress`, `Seats`, `latitude`, `longitude` |
| `HallsTime-good.xlsx` (9×9) | HallTransition | строки/столбцы = названия залов, значение = минуты; **обе направленности присутствуют** |
| `ArtistDetails-good.xlsx` (200) | Artist + ConcertArtist | `ShowNum`, `Artists`, `Spetial` (особый/хедлайнер) |
| `show_details.xlsx` (391) | Author + Composition + Program | `ShowNum`, `Author`, `Programm` (произведение), `Spetial` |
| `OffProgram-good.xlsx` (21) | OffProgram | `EventNum`, `EventName`, `Description`, `EventDate`, `EventLong`, `HallName`, `Format`, `Recommend` (bool), `link` |
| `GoodOperations.xlsx` (25 830) | Purchase | `ClientId` (= `customer_external_id`), `OpId`, `OpDate`, `ShowId`/`ShowNum`, `HallName`, `ShowDate`, `Price` |
| `RouteRange_with_GMM-.csv` (37 946) | DayRoute + признаки + Archetype | `Sostav` (список `ShowNum`), `Days`, `Concerts`, `Halls`, `ShowTime/TransTime/WaitTime/Costs`, `ComfortScore`, `DepthScore`, `IntellectScore`, `GenreDiversityScore`, `*_qnorm`, `GMM_Cluster` |

**Два разных идентификатора концерта (не схлопываем):**
- **`ShowNum`** — порядковый номер концерта **внутри фестиваля** (1..100). Это локальный ключ связи между `ConcertList`/`ArtistDetails`/`show_details`/`Sostav`. Уникален в пределах одного фестиваля; в другом году нумерация своя.
- **`ShowId`** — идентификатор концерта в **общем каталоге внешней CRM** (где идут продажи), сквозной между фестивалями. По нему приходят покупки (`GoodOperations`) и будущие обновления наличия.

В v3 это два отдельных поля концерта (`show_num`, `crm_show_id`), оба маппятся на наш внутренний `id`, но между собой **не отождествляются** ([02](02-domain-model.md)). Excel-каталог импортируется по `ShowNum`; покупки/наличие из CRM — по `ShowId`.

**Программа (повторы):** `Program.signature` = нормализованное множество пар `(Author, Programm)` по `ShowNum` из `show_details.xlsx`.

**Замечания по качеству (учесть при импорте):**
- В `HallList` у части залов `latitude/longitude = 0` → координатная оценка перехода невозможна, такой переход даёт `no_data` (см. [03](03-route-engine.md#правила-конфликтов)).
- В дампе `GoodOperations` поле `OpDate` встречается с эпохой 1970 — это **артефакт конвертации форматов колонок** (тип/формат даты при выгрузке), а не реально отсутствующие данные. Импорт должен корректно распознавать форматы дат (datetime/строка/Excel-serial) и валидировать результат; для режима наличия `sim_replay` нужны правильно распарсенные `purchased_at`.
- `RouteRange_with_GMM-.csv` содержит маршруты **только одного фестивального дня** (`Days = 1`) — см. фазу предрасчёта в [03](03-route-engine.md#когда-и-для-каких-дней-считаем) и [99](99-current-system-audit.md).

## Конфигурация

Один `config.py` (pydantic-settings, из `.env`). Всё, что в v2 было хардкодом, — здесь: пороги конфликтов (`buffer_tight_minutes`, `buffer_overlap_slack`, `default_concert_minutes`, `walk_speed_m_per_min`), параметры наличия (модель, seed, форма кривой, частота тика), часы (дефолтный режим), SMTP, веса анкеты по умолчанию.

## Нагрузка и масштаб

~5000 зрителей за фестиваль → пик десятки одновременных запросов. FastAPI + Postgres справятся с запасом. Тяжёлое (предрасчёт маршрутов) — офлайн. Кэш доступных маршрутов — разделяемый (Redis), чтобы инвалидация при изменении наличия видна всем воркерам; in-process допустим только при `--workers 1`. **Брокеры/горизонтальное масштабирование не нужны** — вводим только при появлении бота с рассылками. Перф-бюджеты и план нагрузочного теста (через `accelerated`-часы) — в [08](08-cross-cutting.md#производительность-и-нагрузка).

## Тестирование

- Доменное ядро покрывается юнит-тестами без БД/HTTP (чистые функции конфликтов, комбинирования, скоринга).
- `FestivalClock` инъектируется → тесты времени детерминированы (offset/accelerated в тестах = фиктивные часы).
- Эмуляция (curve/replay) воспроизводима по seed → интеграционные тесты наличия и уведомлений.
