# 🤝 Руководство по контрибьюции

Спасибо за интерес к проекту Figaro Festival! Мы приветствуем вклад от сообщества.

## 📋 Содержание

- [🚀 Быстрый старт](#-быстрый-старт)
- [🐛 Сообщение об ошибках](#-сообщение-об-ошибках)
- [💡 Предложение новых функций](#-предложение-новых-функций)
- [🔧 Процесс разработки](#-процесс-разработки)
- [📝 Стандарты кода](#-стандарты-кода)
- [🧪 Тестирование](#-тестирование)
- [📚 Документация](#-документация)
- [🎯 Роли в проекте](#-роли-в-проекте)

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.11+
- Docker и Docker Compose
- Git
- Знание FastAPI, SQLModel, Celery

### Настройка окружения разработки

```bash
# Форкните репозиторий
git clone https://github.com/YOUR_USERNAME/figaro-festival.git
cd figaro-festival

# Добавьте upstream
git remote add upstream https://github.com/original-owner/figaro-festival.git

# Создайте ветку для разработки
git checkout -b feature/your-feature-name

# Установите зависимости
pip install -r app/requirements.txt
pip install -r worker/requirements.txt
pip install -r bot/requirements.txt

# Запустите базу данных
docker compose up db -d

# Запустите приложение
cd app && uvicorn api:app --reload
```

## 🐛 Сообщение об ошибках

### Создание Issue

1. **Проверьте существующие Issues** - возможно, ваша проблема уже известна
2. **Используйте шаблон** - заполните все поля в шаблоне Bug Report
3. **Предоставьте детали**:
   - Описание проблемы
   - Шаги для воспроизведения
   - Ожидаемое и фактическое поведение
   - Скриншоты (если применимо)
   - Версии ПО (Python, Docker, etc.)

### Пример хорошего Issue

```markdown
## Описание
При попытке получить рекомендации для пользователя с ID 123 возникает ошибка 500.

## Шаги для воспроизведения
1. Авторизуйтесь как пользователь с ID 123
2. Перейдите на страницу рекомендаций
3. Нажмите "Получить рекомендации"

## Ожидаемое поведение
Должны отобразиться персонализированные рекомендации

## Фактическое поведение
Ошибка 500 Internal Server Error

## Дополнительная информация
- Python 3.11.0
- FastAPI 0.104.1
- PostgreSQL 15
```

## 💡 Предложение новых функций

### Создание Feature Request

1. **Обсудите идею** в Discussions перед созданием Issue
2. **Используйте шаблон** Feature Request
3. **Обоснуйте необходимость**:
   - Какую проблему решает функция?
   - Кто будет использовать эту функцию?
   - Как это улучшит проект?

### Пример хорошего Feature Request

```markdown
## Описание функции
Добавить возможность экспорта маршрута в календарь (iCal формат)

## Обоснование
Пользователи хотят добавлять концерты в свои календари для планирования

## Предлагаемая реализация
- Добавить кнопку "Экспорт в календарь" в личном кабинете
- Генерировать .ics файл с концертами
- Включить информацию о времени, месте, исполнителях

## Альтернативы
Рассматривались интеграции с Google Calendar API, но iCal проще в реализации
```

## 🔧 Процесс разработки

### Workflow

1. **Создайте Issue** для вашей задачи
2. **Форкните репозиторий** и создайте ветку
3. **Разработайте функцию** с тестами
4. **Обновите документацию** при необходимости
5. **Создайте Pull Request**

### Создание ветки

```bash
# Создание ветки для новой функции
git checkout -b feature/export-to-calendar

# Создание ветки для исправления бага
git checkout -b fix/recommendation-500-error

# Создание ветки для документации
git checkout -b docs/api-examples
```

### Коммиты

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Новые функции
git commit -m "feat: add calendar export functionality"

# Исправления багов
git commit -m "fix: resolve 500 error in recommendations API"

# Документация
git commit -m "docs: add API usage examples"

# Рефакторинг
git commit -m "refactor: optimize database queries"

# Тесты
git commit -m "test: add unit tests for calendar export"
```

### Pull Request

1. **Заполните шаблон** PR
2. **Опишите изменения** подробно
3. **Добавьте тесты** для новой функциональности
4. **Обновите документацию** при необходимости
5. **Проверьте CI/CD** pipeline

## 📝 Стандарты кода

### Python

- **PEP 8** - стиль кода
- **Black** - форматирование
- **isort** - сортировка импортов
- **mypy** - типизация
- **flake8** - линтинг

### Настройка pre-commit

```bash
# Установка pre-commit
pip install pre-commit

# Настройка хуков
pre-commit install

# Запуск на всех файлах
pre-commit run --all-files
```

### Пример .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

### Документирование кода

```python
def get_user_recommendations(user_id: int, limit: int = 10) -> List[Recommendation]:
    """
    Получить персонализированные рекомендации для пользователя.
    
    Args:
        user_id: ID пользователя
        limit: Максимальное количество рекомендаций
        
    Returns:
        Список рекомендаций
        
    Raises:
        UserNotFoundError: Если пользователь не найден
        NoPreferencesError: Если у пользователя нет предпочтений
    """
    # Реализация...
```

## 🧪 Тестирование

### Типы тестов

- **Unit тесты** - тестирование отдельных функций
- **Integration тесты** - тестирование взаимодействия компонентов
- **API тесты** - тестирование эндпоинтов
- **E2E тесты** - тестирование полного пользовательского сценария

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный тест
pytest tests/test_recommendations.py::test_get_user_recommendations

# Параллельное выполнение
pytest -n auto
```

### Написание тестов

```python
import pytest
from fastapi.testclient import TestClient
from app.api import app

client = TestClient(app)

def test_get_recommendations():
    """Тест получения рекомендаций."""
    response = client.get("/api/recommendations", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert "recommendations" in response.json()

@pytest.mark.asyncio
async def test_create_user():
    """Тест создания пользователя."""
    user_data = {"email": "test@example.com", "password": "password123"}
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

## 📚 Документация

### Обновление документации

- **README.md** - основная документация
- **API docs** - документация API (автогенерируется)
- **Inline docs** - документация в коде
- **Tutorials** - обучающие материалы

### Стандарты документации

- Используйте **Markdown** для текстовой документации
- Добавляйте **примеры кода** с комментариями
- Включайте **диаграммы** для сложных концепций
- Обновляйте **CHANGELOG.md** при изменениях

## 🎯 Роли в проекте

### Maintainers
- **Code Review** - проверка PR
- **Release Management** - управление релизами
- **Architecture Decisions** - принятие архитектурных решений

### Contributors
- **Feature Development** - разработка новых функций
- **Bug Fixes** - исправление ошибок
- **Documentation** - улучшение документации

### Reviewers
- **Code Quality** - проверка качества кода
- **Testing** - проверка тестового покрытия
- **Security** - проверка безопасности

## 🏆 Признание вклада

Мы признаем вклад участников:

- **Contributors** - в README.md
- **Release Notes** - в CHANGELOG.md
- **GitHub** - автоматически в Insights

## 📞 Получение помощи

- **Issues** - для багов и предложений
- **Discussions** - для общих вопросов
- **Telegram** - для быстрой связи
- **Email** - для приватных вопросов

---

Спасибо за ваш вклад в развитие Figaro Festival! 🎵 