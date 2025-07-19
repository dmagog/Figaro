# Тесты для API Figaro Bot

Этот каталог содержит комплексные тесты для API приложения Figaro Bot, написанные с использованием pytest.

## Структура тестов

```
tests/
├── conftest.py              # Конфигурация pytest и фикстуры
├── test_auth.py             # Тесты аутентификации
├── test_user.py             # Тесты пользователей
├── test_purchase.py         # Тесты покупок
├── test_home.py             # Тесты главной страницы и админки
├── test_tickets.py          # Тесты билетов
├── requirements-test.txt    # Зависимости для тестирования
└── README.md               # Этот файл
```

## Установка зависимостей

```bash
pip install -r tests/requirements-test.txt
```

## Запуск тестов

### Запуск всех тестов
```bash
pytest tests/
```

### Запуск с подробным выводом
```bash
pytest tests/ -v
```

### Запуск с покрытием кода
```bash
pytest tests/ --cov=app --cov-report=html
```

### Запуск конкретного теста
```bash
pytest tests/test_auth.py::TestAuthAPI::test_login_page_get -v
```

### Запуск тестов с параллельным выполнением
```bash
pytest tests/ -n auto
```

## Фикстуры

### Основные фикстуры

- `app` - Тестовое FastAPI приложение
- `client` - Тестовый HTTP клиент
- `db_session` - Сессия тестовой базы данных
- `test_user` - Тестовый пользователь
- `test_concert` - Тестовый концерт
- `test_hall` - Тестовый зал
- `test_purchase` - Тестовая покупка
- `auth_headers` - Заголовки авторизации

### Использование фикстур

```python
def test_example(client: TestClient, test_user, auth_headers):
    response = client.get("/profile", headers=auth_headers)
    assert response.status_code == 200
```

## Типы тестов

### 1. Тесты аутентификации (`test_auth.py`)
- Регистрация и вход пользователей
- Валидация токенов
- Обработка ошибок аутентификации
- Тестирование форм входа и регистрации

### 2. Тесты пользователей (`test_user.py`)
- CRUD операции с пользователями
- Профиль пользователя
- Управление external_id
- Отладочные эндпоинты

### 3. Тесты покупок (`test_purchase.py`)
- Получение информации о покупках
- Фильтрация по датам
- Статистика покупок
- Структура данных покупок

### 4. Тесты главной страницы (`test_home.py`)
- Доступ к админским страницам
- Проверка прав доступа
- API маршрутов
- Управление контентом

### 5. Тесты билетов (`test_tickets.py`)
- Доступность билетов
- Статус сервиса билетов
- Кэширование
- Обработка ошибок

## Настройка тестовой среды

### База данных
Тесты используют SQLite в памяти для изоляции и скорости выполнения.

### Переменные окружения
Тесты автоматически настраивают тестовую среду, но при необходимости можно установить:

```bash
export TESTING=True
export DATABASE_URL=sqlite:///:memory:
```

## Лучшие практики

### 1. Изоляция тестов
Каждый тест должен быть независимым и не влиять на другие тесты.

### 2. Использование фикстур
Используйте фикстуры для создания тестовых данных вместо хардкода.

### 3. Проверка структуры ответов
Проверяйте не только статус кода, но и структуру возвращаемых данных.

### 4. Тестирование ошибок
Тестируйте как успешные сценарии, так и обработку ошибок.

### 5. Документирование тестов
Каждый тест должен иметь понятное описание того, что он проверяет.

## Примеры тестов

### Тест успешного входа
```python
def test_login_success(self, client: TestClient, test_user, test_user_data):
    response = client.post(
        "/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 302  # Редирект после успешного входа
    assert "access_token" in response.cookies
```

### Тест API эндпоинта
```python
def test_get_user_profile(self, client: TestClient, test_user, auth_headers):
    response = client.get("/profile", headers=auth_headers)
    assert response.status_code == 200
    assert "profile.html" in response.text
```

### Тест обработки ошибок
```python
def test_user_not_found(self, client: TestClient):
    response = client.get("/email/nonexistent@example.com")
    assert response.status_code == 404
    assert "User does not exist" in response.json()["detail"]
```

## Отладка тестов

### Запуск с отладкой
```bash
pytest tests/ -s --pdb
```

### Логирование
```bash
pytest tests/ --log-cli-level=DEBUG
```

### Покрытие кода
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

## Интеграция с CI/CD

Тесты можно интегрировать в CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r tests/requirements-test.txt
      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml
```

## Поддержка

При возникновении проблем с тестами:

1. Проверьте, что все зависимости установлены
2. Убедитесь, что тестовая база данных доступна
3. Проверьте логи тестов на наличие ошибок
4. Убедитесь, что API сервер не запущен (тесты используют тестовый клиент) 