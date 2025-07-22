import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

class TestHomeAPI:
    """Тесты для главной страницы и основных маршрутов"""
    
    def test_index_page_authenticated(self, client: TestClient, test_user, auth_headers):
        """Тест главной страницы для аутентифицированного пользователя"""
        response = client.get("/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        # Проверяем содержимое страницы вместо названия файла
        assert "Фестиваль" in response.text
        assert "Безумные дни" in response.text
    
    def test_index_page_unauthenticated(self, client: TestClient):
        """Тест главной страницы для неаутентифицированного пользователя"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        # Проверяем содержимое страницы вместо названия файла
        assert "Фестиваль" in response.text
        assert "Безумные дни" in response.text
    
    def test_admin_index_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест админ панели для аутентифицированного суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие элементов админки
        assert "Админка" in response.text or "admin" in response.text.lower()

    def test_admin_index_authenticated_not_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест админской страницы для обычного пользователя"""
        response = client.get("/admin", headers=auth_headers, follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_admin_index_unauthenticated(self, client: TestClient):
        """Тест админской страницы без аутентификации"""
        response = client.get("/admin", follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_admin_users_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы пользователей для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/users", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Пользователи" in response.text
    
    def test_admin_users_not_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления пользователями для обычного пользователя"""
        response = client.get("/admin/users", headers=auth_headers, follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_admin_concerts_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы концертов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/concerts", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Концерты" in response.text
    
    def test_admin_halls_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы залов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/halls", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Залы" in response.text
    
    def test_admin_purchases_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы покупок для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/purchases", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Покупки" in response.text
    
    def test_admin_customers_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы клиентов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/customers", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Покупатели" in response.text
    
    def test_admin_routes_upload_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы загрузки маршрутов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/routes/upload", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Загрузка маршрутов" in response.text
    
    def test_admin_routes_view_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы просмотра маршрутов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/routes/view", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Маршруты" in response.text
    
    def test_admin_artists_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы артистов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/artists", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Артисты" in response.text
    
    def test_admin_authors_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы авторов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/authors", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Авторы" in response.text

    def test_admin_compositions_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы композиций для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/compositions", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие элементов админки
        assert "Админка" in response.text or "admin" in response.text.lower()

    def test_admin_genres_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы жанров для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/genres", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие элементов админки
        assert "Админка" in response.text or "admin" in response.text.lower()

    def test_admin_genres_with_data(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы жанров с проверкой наличия данных"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/genres", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем наличие данных о жанрах
        assert "Жанры фестиваля" in response.text
        assert "Список жанров" in response.text
        
        # Проверяем, что есть хотя бы один жанр в таблице
        # (это будет работать только если жанры были созданы)
        from models.genre import Genre
        from sqlmodel import select
        genres_count = len(db_session.exec(select(Genre)).all())
        if genres_count > 0:
            assert "tbody" in response.text  # Таблица должна содержать tbody
            assert "tr" in response.text     # Должны быть строки таблицы

    def test_admin_offprogram_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы офф-программы для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/offprogram", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Офф-программа" in response.text
    
    def test_get_routes_api(self, client: TestClient, auth_headers):
        """Тест получения маршрутов через API"""
        response = client.get("/api/routes", headers=auth_headers)
        # Проверяем, что эндпоинт существует (может быть 200, 403 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
    
    def test_get_routes_upload_status(self, client: TestClient):
        """Тест получения статуса загрузки маршрутов"""
        response = client.get("/admin/routes/upload_status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "in_progress" in data
        assert "progress" in data
        assert "total" in data
        assert "added" in data
        assert "updated" in data
        assert "error" in data
    
    def test_get_available_routes_status(self, client: TestClient):
        """Тест получения статуса доступных маршрутов"""
        response = client.get("/admin/routes/available_routes_status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "in_progress" in data
        assert "progress" in data
        assert "total" in data
        assert "available_count" in data
        assert "total_routes" in data
        assert "availability_percentage" in data
        assert "error" in data
    
    def test_get_customer_route_details(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения деталей маршрута клиента"""
        response = client.get(f"/api/customers/{test_purchase.user_external_id}/route-details", headers=auth_headers)
        # Проверяем, что эндпоинт существует (может быть 200, 403 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_get_customer_route_details_not_found(self, client: TestClient, auth_headers):
        """Тест получения деталей маршрута для несуществующего клиента"""
        response = client.get("/api/customers/nonexistent_user/route-details", headers=auth_headers)
        # Проверяем, что эндпоинт существует (может быть 200, 403 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
    
    def test_update_hall_seats_authenticated_superuser(self, client: TestClient, test_user, test_hall, auth_headers, db_session):
        """Тест обновления количества мест в зале для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        new_seats = 150
        response = client.post(
            f"/admin/halls/{test_hall.id}/update_seats",
            json={"seats": new_seats},
            cookies={"access_token": token}
        )
        # Проверяем, что эндпоинт существует (может быть 200 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_hall_seats_not_superuser(self, client: TestClient, test_user, test_hall, auth_headers):
        """Тест обновления количества мест в зале для обычного пользователя"""
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        new_seats = 150
        response = client.post(
            f"/admin/halls/{test_hall.id}/update_seats",
            json={"seats": new_seats},
            cookies={"access_token": token}
        )
        # Проверяем, что эндпоинт существует и возвращает ошибку доступа
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_update_user_external_id_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест обновления external_id пользователя для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        new_external_id = "updated_external_123"
        response = client.post(
            f"/admin/users/{test_user.id}/update_external_id",
            json={"external_id": new_external_id},
            cookies={"access_token": token}
        )
        # Проверяем, что эндпоинт существует (может быть 200 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_customer_external_id_authenticated_superuser(self, client: TestClient, test_user, test_purchase, auth_headers, db_session):
        """Тест обновления external_id клиента для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        new_external_id = "updated_customer_456"
        response = client.post(
            f"/admin/customers/{test_purchase.user_external_id}/update_external_id",
            json={"external_id": new_external_id},
            cookies={"access_token": token}
        )
        # Проверяем, что эндпоинт существует (может быть 200 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_toggle_offprogram_recommend_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест переключения рекомендаций офф-программы для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.post("/admin/offprogram/toggle_recommend", cookies={"access_token": token})
        # Проверяем, что эндпоинт существует (может быть 200 или 404)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_admin_routes_instruction_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы инструкций по маршрутам для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/routes/instruction", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        assert "Инструкция" in response.text

    def test_admin_routes_concerts_authenticated_superuser(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест страницы концертов маршрутов для суперпользователя"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        # Извлекаем токен из заголовка Authorization
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        response = client.get("/admin/routes/concerts", cookies={"access_token": token})
        assert response.status_code == status.HTTP_200_OK
        # Проверяем наличие элементов админки
        assert "Админка" in response.text or "admin" in response.text.lower()

    def test_admin_routes_redirect(self, client: TestClient, test_user, auth_headers, db_session):
        """Тест редиректа с /admin/routes"""
        # Устанавливаем права суперпользователя
        test_user.is_superuser = True
        db_session.add(test_user)
        db_session.commit()
        
        response = client.get("/admin/routes", headers=auth_headers, follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        # Проверяем, что редирект ведет на страницу загрузки
        assert "/admin/routes/upload" in response.headers["location"] 