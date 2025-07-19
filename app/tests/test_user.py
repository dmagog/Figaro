import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models.user import User

class TestUserAPI:
    """Тесты для API пользователей"""
    
    def test_signup_success(self, client: TestClient, db_session: Session):
        """Тест успешной регистрации пользователя"""
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "name": "New User"  # Исправлено: используем name вместо first_name и last_name
        }
        
        response = client.post("/signup", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что пользователь создан в базе
        from services.crud import user as UserService
        user = UserService.get_user_by_email(user_data["email"], db_session)
        assert user is not None
        assert user.name == user_data["name"]  # Исправлено: проверяем name
    
    def test_signup_existing_user(self, client: TestClient, test_user):
        """Тест регистрации существующего пользователя"""
        user_data = {
            "email": test_user.email,
            "password": "newpassword123",
            "name": "New User"  # Исправлено: используем name
        }
        
        response = client.post("/signup", json=user_data)
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "User with email provided exists already" in data["detail"]
    
    def test_signup_invalid_data(self, client: TestClient):
        """Тест регистрации с неверными данными"""
        user_data = {
            "email": "invalid-email",
            "password": "123",  # Слишком короткий пароль
            "name": ""  # Исправлено: используем name
        }
        
        response = client.post("/signup", json=user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_signin_success(self, client: TestClient, test_user, test_user_data):
        """Тест успешного входа пользователя"""
        response = client.post(
            "/signin",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
    
    def test_signin_invalid_credentials(self, client: TestClient):
        """Тест входа с неверными учетными данными"""
        response = client.post(
            "/signin",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_signin_wrong_password(self, client: TestClient, test_user):
        """Тест входа с неверным паролем"""
        response = client.post(
            "/signin",
            data={
                "username": test_user.email,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_by_email_success(self, client: TestClient, test_user):
        """Тест получения пользователя по email"""
        response = client.get(f"/email/{test_user.email}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name  # Исправлено: проверяем name вместо first_name
        # Пароль не должен возвращаться
        assert "password" not in data
    
    def test_get_user_by_email_not_found(self, client: TestClient):
        """Тест получения несуществующего пользователя по email"""
        response = client.get("/email/nonexistent@example.com")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_user_by_id_success(self, client: TestClient, test_user):
        """Тест получения пользователя по ID"""
        response = client.get(f"/id/{test_user.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name  # Исправлено: проверяем name вместо first_name
        # Пароль не должен возвращаться
        assert "password" not in data
    
    def test_get_user_by_id_not_found(self, client: TestClient):
        """Тест получения несуществующего пользователя по ID"""
        response = client.get("/id/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_all_users_success(self, client: TestClient, test_user):
        """Тест получения всех пользователей"""
        response = client.get("/get_all_users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Проверяем, что наш тестовый пользователь в списке
        user_emails = [user["email"] for user in data]
        assert test_user.email in user_emails
        
        # Проверяем, что пароли не возвращаются
        for user in data:
            assert "password" not in user
    
    def test_profile_page_authenticated(self, client: TestClient, test_user, auth_headers):
        """Тест страницы профиля для аутентифицированного пользователя"""
        response = client.get("/profile", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "profile.html" in response.text
    
    def test_profile_page_unauthenticated(self, client: TestClient):
        """Тест страницы профиля для неаутентифицированного пользователя"""
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_set_external_id_success(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест установки external_id"""
        new_external_id = "new_external_456"
        response = client.post(
            "/profile/set_external_id",
            json={"external_id": new_external_id},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что external_id обновлен в базе
        from services.crud import user as UserService
        updated_user = UserService.get_user_by_email(test_user.email, db_session)
        assert updated_user.external_id == new_external_id
    
    def test_set_external_id_unauthenticated(self, client: TestClient):
        """Тест установки external_id без аутентификации"""
        response = client.post(
            "/profile/set_external_id",
            json={"external_id": "new_external_456"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_debug_user_external_id_success(self, client: TestClient, test_user):
        """Тест отладочного эндпоинта для получения external_id"""
        response = client.get(f"/debug/user/{test_user.email}/external_id")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["external_id"] == test_user.external_id
    
    def test_debug_user_external_id_not_found(self, client: TestClient):
        """Тест отладочного эндпоинта для несуществующего пользователя"""
        response = client.get("/debug/user/nonexistent@example.com/external_id")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_set_user_external_id_success(self, client: TestClient, test_user, db_session):
        """Тест установки external_id через отладочный эндпоинт"""
        new_external_id = "debug_external_789"
        response = client.post(f"/debug/user/{test_user.email}/set_external_id/{new_external_id}")
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что external_id обновлен
        from services.crud import user as UserService
        updated_user = UserService.get_user_by_email(test_user.email, db_session)
        assert updated_user.external_id == new_external_id
    
    def test_debug_user_purchases_success(self, client: TestClient, test_purchase):
        """Тест отладочного эндпоинта для получения покупок пользователя"""
        response = client.get(f"/debug/purchases/{test_purchase.user_external_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)  # Исправлено: ожидаем словарь
        assert "purchases" in data
        assert isinstance(data["purchases"], list)
        assert len(data["purchases"]) >= 1
        # Проверяем, что покупка принадлежит правильному пользователю
        assert data["external_id"] == test_purchase.user_external_id
    
    def test_debug_user_purchases_empty(self, client: TestClient):
        """Тест отладочного эндпоинта для пользователя без покупок"""
        response = client.get("/debug/purchases/nonexistent_external_id")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)  # Исправлено: ожидаем словарь
        assert "purchases" in data
        assert isinstance(data["purchases"], list)
        assert len(data["purchases"]) == 0
    
    def test_debug_transitions(self, client: TestClient):
        """Тест отладочного эндпоинта для переходов"""
        response = client.get("/debug/transitions")
        assert response.status_code == status.HTTP_200_OK
        # Проверяем, что возвращается JSON
        data = response.json()
        assert isinstance(data, dict) 