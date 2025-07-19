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
        assert "login.html" in response.text
    
    def test_register_page_get(self, client: TestClient):
        """Тест получения страницы регистрации"""
        response = client.get("/register")
        assert response.status_code == status.HTTP_200_OK
        assert "register.html" in response.text
    
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
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            },
            follow_redirects=False
        )
        assert response.status_code == status.HTTP_302_FOUND
        assert "access_token" in response.cookies
    
    def test_login_post_invalid_credentials(self, client: TestClient):
        """Тест входа с неверными учетными данными"""
        response = client.post(
            "/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        assert "Incorrect Email or Password" in response.text
    
    def test_logout(self, client: TestClient, auth_headers):
        """Тест выхода из системы"""
        # Сначала входим
        response = client.get("/logout")
        assert response.status_code == status.HTTP_302_FOUND
        
        # Проверяем, что cookie удален
        assert "access_token" not in response.cookies or response.cookies["access_token"] == ""
    
    def test_register_post_success(self, client: TestClient, db_session: Session):
        """Тест успешной регистрации"""
        response = client.post(
            "/register",
            data={
                "email": "newuser@example.com",
                "password": "newpassword123",
                "first_name": "New",
                "last_name": "User"
            },
            follow_redirects=False
        )
        assert response.status_code == status.HTTP_302_FOUND
        
        # Проверяем, что пользователь создан в базе
        from services.crud import user as UserService
        user = UserService.get_user_by_email("newuser@example.com", db_session)
        assert user is not None
        assert user.first_name == "New"
        assert user.last_name == "User"
    
    def test_register_post_existing_user(self, client: TestClient, test_user):
        """Тест регистрации существующего пользователя"""
        response = client.post(
            "/register",
            data={
                "email": test_user.email,
                "password": "newpassword123",
                "first_name": "New",
                "last_name": "User"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        assert "User with email provided exists already" in response.text
    
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