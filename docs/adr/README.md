# Architecture Decision Records (ADR)

Ключевые архитектурные решения v3 — с контекстом и последствиями, чтобы будущие участники понимали «почему так», а не только «как». Формат: краткий [MADR](https://adr.github.io/madr/).

Статусы: `accepted` (принято), `proposed` (предложено), `superseded by NNNN` (заменено).

| # | Решение | Статус |
|---|---------|--------|
| [0001](0001-server-rendered-htmx.md) | Server-rendered + HTMX вместо SPA | accepted |
| [0002](0002-no-broker-in-mvp.md) | Без брокера сообщений в MVP (outbox + планировщик) | accepted |
| [0003](0003-bdd-behave-russian-gherkin.md) | BDD на behave с русским Gherkin | accepted |
| [0004](0004-two-availability-models.md) | Две модели наличия: кривая и реплей покупок | accepted |
| [0005](0005-festival-clock.md) | Управляемое время через FestivalClock | accepted |
| [0006](0006-accounts-and-rbac.md) | Аккаунты + реальный RBAC (user/researcher/admin) | accepted |
| [0007](0007-single-db-festival-scoping.md) | Один DB со скоупом по фестивалю (festival_id) | accepted |

Новое решение — новый файл с возрастающим номером; не переписываем принятые, а помечаем `superseded`.
