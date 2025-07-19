import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from auth.hash_password import HashPassword

class TestAuthAPI:
    """Тесты для API аутентификации"""
    
    def test_login_page_get(self, client: TestClient):
        """Тест получения страницы входа"""
        response = client.get("/login")
        assert response.status_code == status.HTTP_200_OK
        # Проверяем содержимое страницы вместо названия файла
        assert "Вход" in response.text
        assert "Добро пожаловать" in response.text
        assert "email" in response.text
        assert "password" in response.text
    
    def test_register_page_get(self, client: TestClient):
        """Тест получения страницы регистрации"""
        response = client.get("/register")
        assert response.status_code == status.HTTP_200_OK
        # Проверяем содержимое страницы вместо названия файла
        assert "Регистрация" in response.text
        assert "Создать аккаунт" in response.text
        assert "email" in response.text
        assert "password" in response.text
    
    def test_token_endpoint_success(self, client: TestClient, test_user, test_user_data):
        """Тест успешного получения токена"""
        response = client.post(
            "/token",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_token_endpoint_invalid_credentials(self, client: TestClient):
        """Тест получения токена с неверными учетными данными"""
        response = client.post(
            "/token",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_token_endpoint_wrong_password(self, client: TestClient, test_user):
        """Тест получения токена с неверным паролем"""
        response = client.post(
            "/token",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_post_success(self, client: TestClient, test_user, test_user_data):
        """Тест успешного входа через форму"""
        response = client.post(
            "/login",
            data={
                "email": test_user_data["email"],
                "password": test_user_data["password"]
            },
            follow_redirects=False
        )
        # После успешного входа должен быть редирект
        assert response.status_code == status.HTTP_302_FOUND
        assert "/" in response.headers["location"]

    def test_login_post_invalid_credentials(self, client: TestClient):
        """Тест входа с неверными учетными данными через форму"""
        response = client.post(
            "/login",
            data={
                "email": "invalid@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие сообщения об ошибке
        assert "Valid email is required" in response.text or "error" in response.text.lower()
    
    def test_logout(self, client: TestClient, test_user, auth_headers):
        """Тест выхода из системы"""
        response = client.get("/logout", headers=auth_headers, follow_redirects=False)
        # После выхода должен быть редирект (307 или 302)
        assert response.status_code in [status.HTTP_302_FOUND, 307]
        assert "/" in response.headers["location"]
    
    def test_register_post_success(self, client: TestClient):
        """Тест успешной регистрации через форму"""
        response = client.post(
            "/register",
            data={
                "name": "New User",
                "email": "newuser@example.com",
                "password": "newpassword123"
            },
            follow_redirects=False
        )
        # Проверяем успешную регистрацию (может быть 200 или 302)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_302_FOUND]
        if response.status_code == status.HTTP_302_FOUND:
            assert "/login" in response.headers["location"]
        else:
            # Если 200, проверяем, что это страница регистрации (не ошибка)
            assert "Регистрация" in response.text
            assert "Создать аккаунт" in response.text
    
    def test_register_post_existing_user(self, client: TestClient, test_user):
        """Тест регистрации существующего пользователя через форму"""
        response = client.post(
            "/register",
            data={
                "name": "Test User",
                "email": test_user.email,
                "password": "newpassword123"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие сообщения об ошибке
        assert "error" in response.text.lower() or "уже существует" in response.text.lower()
    
    def test_register_post_invalid_data(self, client: TestClient):
        """Тест регистрации с неверными данными"""
        response = client.post(
            "/register",
            data={
                "email": "invalid-email",
                "password": "123",  # Слишком короткий пароль
                "first_name": "",
                "last_name": ""
            }
        )
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие ошибок валидации
        assert "error" in response.text.lower() or "invalid" in response.text.lower()
    
    def test_token_endpoint_missing_data(self, client: TestClient):
        """Тест получения токена без данных"""
        response = client.post("/token")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_post_missing_data(self, client: TestClient):
        """Тест входа без данных"""
        response = client.post("/login")
        assert response.status_code == status.HTTP_200_OK
        # Должны быть ошибки валидации
        assert "error" in response.text.lower() or "invalid" in response.text.lower()
    
    def test_register_post_missing_data(self, client: TestClient):
        """Тест регистрации без данных"""
        response = client.post("/register")
        assert response.status_code == status.HTTP_200_OK
        # Должны быть ошибки валидации
        assert "error" in response.text.lower() or "invalid" in response.text.lower() 