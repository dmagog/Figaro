# 07 — BDD: подход, конвенции, цикл

Реализацию v3 ведём через **BDD**: сначала описываем поведение сценариями на русском Gherkin, согласуем их как контракт, затем пишем код до зелёного прогона. Сценарии — одновременно спецификация, приёмочные тесты и living documentation для заказчика/исследователя.

- **Фреймворк:** [behave](https://behave.readthedocs.io) (Python).
- **Язык:** русский Gherkin — первая строка файла `# language: ru` (`Функция/Предыстория/Сценарий/Структура сценария/Примеры`, шаги `Дано/Когда/Тогда/И/Но`).
- **Где живут фичи:** канонически — в [`features/`](features/) этой спеки; репозиторий v3 поднимает эти же `.feature` в свой тест-набор.

## Почему BDD ложится на нашу архитектуру

- Доменное ядро отделено от веба ([05](05-architecture-and-platform.md)) → шаги тестируют **домен** напрямую (быстро, без HTTP); веб-шаги тонкие.
- Пороги переходов — `Структура сценария` + `Примеры` закрывают все граничные случаи одной фичей ([features/transitions.feature](features/transitions.feature)).
- `FestivalClock` инъектируется → сценарии времени детерминированы («Дано часы в режиме accelerated…»).
- Эмуляция воспроизводима по seed → наличие и уведомления проверяются сценарием.

## Структура в репозитории v3

```
features/
├── *.feature              # поведение на русском Gherkin (контракт)
├── environment.py         # хуки: чистая БД и FestivalClock на каждый сценарий
├── steps/
│   ├── clock_steps.py
│   ├── routing_steps.py
│   ├── sheet_steps.py
│   └── ...                # реализация шагов (Python), вызывает domain/services
└── fixtures/              # тестовые наборы данных (мини-каталог фестиваля)
```

`environment.py` (скелет):

```python
def before_scenario(context, scenario):
    context.clock = FixedFestivalClock()   # управляемое виртуальное время
    context.db = create_test_db()          # изолированная БД на сценарий
    context.world = TestWorld(context.db, context.clock)

def after_scenario(context, scenario):
    context.db.rollback()
```

Шаг (иллюстративно — текст русский, функция английская):

```python
# features/steps/clock_steps.py
from behave import given, when, then

@given('часы в режиме "{mode}"')
def step_clock_mode(context, mode):
    context.clock.set_mode(mode)

@then('виртуальная дата равна "{date}"')
def step_assert_virtual_date(context, date):
    assert context.clock.now().date().isoformat() == date
```

## Конвенции

1. **Декларативно, не императивно.** Описываем поведение («концерт добавлен», «показан статус hurry»), а не клики по UI.
2. **Ubiquitous language.** Термины строго из глоссария ([00](00-vision-scope.md#глоссарий)): маршрутный лист, дневной/фестивальный маршрут, накладка, переход, повтор программы, наличие, фаза, архетип. Один термин — один смысл в фичах, доке и коде.
3. **Тестируем домен.** Большинство сценариев бьют по `domain`/`services`. Веб-уровень покрываем отдельными тонкими сценариями (`@web`), не дублируя доменную логику.
4. **`Структура сценария`** для матриц/порогов (переходы, RBAC, режимы часов).
5. **`Предыстория`** для общего контекста фичи (например, «загружен каталог»).
6. **Один файл = одна область поведения.** Без «божественных» фич.
7. **Изоляция и детерминизм.** Чистая БД и фиксированные часы на сценарий; никакого `datetime.now()` в шагах.
8. **Белый ящик помечаем `@domain`.** Сценарии, проверяющие внутреннее состояние («не материализуется как запись в БД»), допустимы на доменном уровне, но тегируются `@domain`, чтобы отличать от чисто поведенческих.

## BDD — не единственный уровень тестов

BDD покрывает **поведение и бизнес-правила**. Алгоритмику (корректность top-k, математику кривой распродажи, формулу `evaluate_transition`, агрегацию признаков, Pareto) дешевле и точнее покрывать **юнит-тестами на pytest**, а веб — парой тонких `@web`-сценариев. Полная пирамида и принцип «не гёркинизировать всё» — в [08](08-cross-cutting.md#пирамида-тестов-чтобы-не-гёркинизировать-всё).

## Фикстуры: мини-каталог фестиваля

Чтобы абстрактные шаги были реализуемы и стабильны, в `features/fixtures/` лежит **маленький детерминированный каталог**: залы `A/B/C/D` с матрицей переходов (как в `transitions.feature`), несколько концертов с временами/программами/жанрами/ценами, пара авторов, программа-дубль для проверки повторов. Сценарии ссылаются на **именованные** сущности из фикстур (зал «A», программа «P», автор «Бах»), а не на «какие-то концерты». `Предыстория`/`environment.py` загружают нужный срез фикстур; время задаётся `FestivalClock`. Это превращает расплывчатые `Дано` (например, «концерты дня, где переход возможен лишь в части пар») в конкретный воспроизводимый набор.

## Теги и запуск

- `@mvp` — входит в MVP.
- `@stage0..@stage7` — привязка к этапу [дорожной карты](06-mvp-roadmap.md).
- Доменные: `@festival @clock @import @routing @anketa @recommend @sheet @suggest @availability @notifications @auth @rbac @security @privacy`.
- Уровневые/контекст: `@domain` (белый ящик/доменный уровень), `@web` (тонкий веб-smoke), `@admin` (админ-сценарии).
- `@growth` — зона роста (вне MVP); `@wip` — в работе (исключается из CI).

Примеры: `behave -t @stage2`, `behave -t @routing`, `behave -t @mvp -t ~@wip`.

## BDD-цикл на каждом этапе

```
1. Написать/согласовать сценарии этапа (.feature)   ← контракт со стейкхолдером
2. Прогнать → красное (шаги падают/не реализованы)
3. Реализовать доменную логику до зелёного
4. Рефакторинг при зелёном
5. Сценарии остаются как регрессия + living docs
```

«Готово» для этапа = все его `@stageN`-сценарии зелёные (см. DoD в [06](06-mvp-roadmap.md)).

## Карта фич по этапам

| Фича | Этап | Тег |
|------|------|-----|
| [clock.feature](features/clock.feature) | 0 | `@clock` |
| [festival_lifecycle.feature](features/festival_lifecycle.feature) | 1–2 | `@admin @festival` |
| [catalog_import.feature](features/catalog_import.feature) | 1 | `@import` |
| [route_engine.feature](features/route_engine.feature) | 2 | `@routing` |
| [transitions.feature](features/transitions.feature) | 2 | `@routing` |
| [auth_roles.feature](features/auth_roles.feature) | 3 | `@auth @rbac` |
| [security.feature](features/security.feature) | 3 | `@security @privacy` |
| [questionnaire.feature](features/questionnaire.feature) | 3 | `@anketa` |
| [recommendations.feature](features/recommendations.feature) | 4 | `@recommend` |
| [route_sheet.feature](features/route_sheet.feature) | 4 | `@sheet` |
| [suggestions.feature](features/suggestions.feature) | 4 | `@suggest` |
| [availability.feature](features/availability.feature) | 5 | `@availability` |
| [notifications.feature](features/notifications.feature) | 6 | `@notifications` |
| [availability_import.feature](features/availability_import.feature) | 7 | `@import @availability` |

## Living documentation

`.feature`-файлы читаемы заказчиком и исследователем без кода. behave умеет генерировать отчёты (`--junit`, плагины формата) — их можно публиковать как актуальную карту поведения сервиса.
