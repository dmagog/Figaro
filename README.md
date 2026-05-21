# Figaro v3

Конструктор персональных маршрутов фестиваля камерной музыки — переписан с нуля, продуктово.

> Спецификация и контракт — в [`docs/`](docs/) (видение, доменная модель, движок маршрутов, эмуляция, архитектура, ADR). Реализацию ведём через **BDD** (behave, русский Gherkin) — сценарии в [`features/`](features/).

## Стек

FastAPI + HTMX + PostgreSQL, планировщик (APScheduler) без брокера. См. [docs/05-architecture-and-platform.md](docs/05-architecture-and-platform.md).

## Быстрый старт (dev)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

pytest          # юнит-тесты
behave          # BDD-сценарии
```

Через Docker:

```bash
cp .env.example .env
docker compose up -d   # app на http://localhost:49080/health
```

## Структура

```
figaro/      доменное ядро (domain), сервисы, web, импорт, batch, scheduler, config
features/    BDD-сценарии (.feature) + steps + fixtures
docs/        спецификация v3 + ADR
data/        исходные выгрузки фестиваля (Excel/CSV)
tests/       юнит-тесты (pytest)
```

## Дорожная карта

По этапам — [docs/06-mvp-roadmap.md](docs/06-mvp-roadmap.md). Версия **3.7.0** — **MVP завершён** (этапы 0–7: каркас, фестиваль+импорт, движок маршрутов, аккаунты/безопасность/анкета, подбор+лист+подсказки, наличие+эмуляция, уведомления, импорт остатков). Дальше — зона роста (бот, дашборды исследователя, разложение покупок по людям, live-API CRM).
