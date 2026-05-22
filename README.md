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

### Через Docker (рекомендуется)

Самодостаточный образ `figaro-v3`: sqlite в `./instance`, код смонтирован (авто-reload),
схема и демо-данные засеиваются при старте.

```bash
docker compose up -d --build      # собрать образ и поднять контейнер
# открыть http://localhost:8754/ · вход: user@figaro.dev / figaro12345
# (admin@figaro.dev — пульт, researcher@figaro.dev — дашборды; пароль тот же)
docker compose logs -f app        # логи
docker compose down               # остановить
```

Изменения в `figaro/**.py` подхватываются авто-reload'ом, шаблоны/CSS — на лету (нужно лишь обновить вкладку). Postgres/redis/scheduler для веб-демо не нужны (добавим для прод-паритета позже).

### Локально (без Docker)

```bash
DATABASE_URL="sqlite:///instance/figaro_dev.db" python -m figaro.web.devseed --data-dir data
DATABASE_URL="sqlite:///instance/figaro_dev.db" uvicorn figaro.web.app:app --port 8754 --reload
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

По этапам — [docs/06-mvp-roadmap.md](docs/06-mvp-roadmap.md). Версия **3.20.0** — **MVP завершён** (этапы 0–7) + офф-программа + **кластеризация маршрутов** на предобработке (k-means, k по силуэту) + **веб-слой** (светлая/тёмная тема, фирменный шрифт и шарик, Bootstrap-иконки; полный авторизационный контур; анкета, подбор под анкету (по кластерам), **сборка маршрута с нуля** из каталога с проверкой конфликтов и сводкой, маршрутный лист карточками с номером концерта, подсказками переходов и дополнением по щелям, админский пульт эмуляции, дашборды исследователя; server-rendered + HTMX). Дальше: телеграм-бот, live-API CRM.
