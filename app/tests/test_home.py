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
        assert "index.html" in response.text
    
    def test_index_page_unauthenticated(self, client: TestClient):
        """Тест главной страницы для неаутентифицированного пользователя"""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "index.html" in response.text
    
    def test_admin_index_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест админской страницы для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_index.html" in response.text
    
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
    
    def test_admin_users_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления пользователями для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/users", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_users.html" in response.text
    
    def test_admin_users_not_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления пользователями для обычного пользователя"""
        response = client.get("/admin/users", headers=auth_headers, follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_admin_concerts_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления концертами для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/concerts", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_concerts.html" in response.text
    
    def test_admin_halls_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления залами для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/halls", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_halls.html" in response.text
    
    def test_admin_purchases_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления покупками для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/purchases", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_purchases.html" in response.text
    
    def test_admin_customers_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления клиентами для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/customers", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_customers.html" in response.text
    
    def test_admin_routes_upload_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы загрузки маршрутов для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/routes/upload", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_routes_upload.html" in response.text
    
    def test_admin_routes_view_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы просмотра маршрутов для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/routes/view", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_routes_view.html" in response.text
    
    def test_admin_artists_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления артистами для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/artists", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_artists.html" in response.text
    
    def test_admin_authors_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления авторами для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/authors", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_authors.html" in response.text
    
    def test_admin_compositions_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления произведениями для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/compositions", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_compositions.html" in response.text
    
    def test_admin_offprogram_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы управления офф-программой для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/offprogram", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_offprogram.html" in response.text
    
    def test_get_routes_api(self, client: TestClient):
        """Тест API получения маршрутов"""
        response = client.get("/api/routes")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
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
    
    def test_get_customer_route_details(self, client: TestClient, test_purchase):
        """Тест получения деталей маршрута клиента"""
        response = client.get(f"/api/customers/{test_purchase.external_id}/route-details")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "external_id" in data
        assert "concerts" in data
        assert isinstance(data["concerts"], list)
    
    def test_get_customer_route_details_not_found(self, client: TestClient):
        """Тест получения деталей маршрута несуществующего клиента"""
        response = client.get("/api/customers/nonexistent_external_id/route-details")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["concerts"] == []
    
    def test_update_hall_seats_authenticated_superuser(self, client: TestClient, test_user, test_hall, auth_headers):
        """Тест обновления количества мест в зале для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.post(
            "/admin/halls/update_seats",
            json={"hall_id": test_hall.id, "seats": 150},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_hall_seats_not_superuser(self, client: TestClient, test_user, test_hall, auth_headers):
        """Тест обновления количества мест в зале для обычного пользователя"""
        response = client.post(
            "/admin/halls/update_seats",
            json={"hall_id": test_hall.id, "seats": 150},
            headers=auth_headers,
            follow_redirects=False
        )
        assert response.status_code == status.HTTP_302_FOUND
        assert "/login" in response.headers["location"]
    
    def test_update_user_external_id_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест обновления external_id пользователя для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        new_external_id = "admin_updated_external_123"
        response = client.post(
            "/admin/users/update_external_id",
            json={"user_id": test_user.id, "external_id": new_external_id},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_customer_external_id_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест обновления external_id клиента для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        new_external_id = "admin_updated_customer_456"
        response = client.post(
            "/admin/customers/update_external_id",
            json={"customer_id": test_user.id, "external_id": new_external_id},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_toggle_offprogram_recommend_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест переключения рекомендации офф-программы для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.post(
            "/api/offprogram/toggle-recommend",
            json={"event_id": 1, "recommend": True},
            headers=auth_headers
        )
        # Может вернуть 200 или 404 в зависимости от существования события
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    def test_admin_routes_instruction_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы инструкций по маршрутам для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/routes/instruction", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_routes_instruction.html" in response.text
    
    def test_admin_routes_concerts_authenticated_superuser(self, client: TestClient, test_user, auth_headers):
        """Тест страницы концертов маршрутов для суперпользователя"""
        # Устанавливаем флаг суперпользователя
        test_user.is_superuser = True
        test_user.__class__.__table__.metadata.bind.commit()
        
        response = client.get("/admin/routes/concerts", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert "admin_routes_concerts.html" in response.text
    
    def test_admin_routes_redirect(self, client: TestClient):
        """Тест редиректа с /admin/routes"""
        response = client.get("/admin/routes", follow_redirects=False)
        assert response.status_code == status.HTTP_302_FOUND
        assert "/admin/routes/view" in response.headers["location"] 