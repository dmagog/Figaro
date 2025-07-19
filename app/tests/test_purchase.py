import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

class TestPurchaseAPI:
    """Тесты для API покупок"""
    
    def test_get_user_purchased_concerts_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения купленных концертов пользователя"""
        response = client.get(
            f"/purchases/concerts/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["user_external_id"] == test_purchase.external_id
        assert data["total_concerts"] >= 1
        assert isinstance(data["concerts"], list)
        
        # Проверяем структуру данных концерта
        if data["concerts"]:
            concert = data["concerts"][0]
            assert "id" in concert
            assert "name" in concert
            assert "datetime" in concert
            assert "hall" in concert
    
    def test_get_user_purchased_concerts_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения купленных концертов без аутентификации"""
        response = client.get(f"/purchases/concerts/{test_purchase.external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_purchased_concerts_empty(self, client: TestClient, auth_headers):
        """Тест получения купленных концертов для пользователя без покупок"""
        response = client.get(
            "/purchases/concerts/nonexistent_external_id",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_concerts"] == 0
        assert data["concerts"] == []
    
    def test_get_user_purchases_with_details_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения детальной информации о покупках"""
        response = client.get(
            f"/purchases/details/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["user_external_id"] == test_purchase.external_id
        assert data["total_purchases"] >= 1
        assert isinstance(data["purchases"], list)
        
        # Проверяем структуру данных покупки
        if data["purchases"]:
            purchase = data["purchases"][0]
            assert "purchased_at" in purchase
            assert "concert" in purchase
            assert "amount" in purchase
    
    def test_get_user_purchases_with_details_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения детальной информации без аутентификации"""
        response = client.get(f"/purchases/details/{test_purchase.external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_purchases_with_details_empty(self, client: TestClient, auth_headers):
        """Тест получения детальной информации для пользователя без покупок"""
        response = client.get(
            "/purchases/details/nonexistent_external_id",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_purchases"] == 0
        assert data["purchases"] == []
    
    def test_get_user_purchase_count_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения количества покупок пользователя"""
        response = client.get(
            f"/purchases/count/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["user_external_id"] == test_purchase.external_id
        assert data["purchase_count"] >= 1
        assert isinstance(data["purchase_count"], int)
    
    def test_get_user_purchase_count_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения количества покупок без аутентификации"""
        response = client.get(f"/purchases/count/{test_purchase.external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_purchase_count_empty(self, client: TestClient, auth_headers):
        """Тест получения количества покупок для пользователя без покупок"""
        response = client.get(
            "/purchases/count/nonexistent_external_id",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["purchase_count"] == 0
    
    def test_get_user_purchases_by_date_range_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок по диапазону дат"""
        # Создаем диапазон дат, включающий текущую дату
        today = datetime.now().date()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = (today + timedelta(days=30)).isoformat()
        
        response = client.get(
            f"/purchases/date-range/{test_purchase.external_id}",
            params={"start_date": start_date, "end_date": end_date},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["user_external_id"] == test_purchase.external_id
        assert data["start_date"] == start_date
        assert data["end_date"] == end_date
        assert "total_concerts" in data
        assert "concerts" in data
        assert isinstance(data["concerts"], list)
    
    def test_get_user_purchases_by_date_range_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения покупок по диапазону дат без аутентификации"""
        today = datetime.now().date()
        start_date = (today - timedelta(days=30)).isoformat()
        end_date = (today + timedelta(days=30)).isoformat()
        
        response = client.get(
            f"/purchases/date-range/{test_purchase.external_id}",
            params={"start_date": start_date, "end_date": end_date}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_purchases_by_date_range_invalid_dates(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок с неверными датами"""
        response = client.get(
            f"/purchases/date-range/{test_purchase.external_id}",
            params={"start_date": "invalid-date", "end_date": "invalid-date"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_user_purchases_by_date_range_missing_params(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок без параметров дат"""
        response = client.get(
            f"/purchases/date-range/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_user_purchase_summary_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения сводки покупок пользователя"""
        response = client.get(
            f"/purchases/summary/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["user_external_id"] == test_purchase.external_id
        assert "total_purchases" in data
        assert "total_spent" in data
        assert "total_concerts" in data
        assert "unique_halls" in data
        assert "genres" in data
        assert isinstance(data["genres"], list)
    
    def test_get_user_purchase_summary_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения сводки покупок без аутентификации"""
        response = client.get(f"/purchases/summary/{test_purchase.external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_user_purchase_summary_empty(self, client: TestClient, auth_headers):
        """Тест получения сводки покупок для пользователя без покупок"""
        response = client.get(
            "/purchases/summary/nonexistent_external_id",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_purchases"] == 0
        assert data["total_spent"] == 0
        assert data["total_concerts"] == 0
        assert data["unique_halls"] == 0
        assert data["genres"] == []
    
    def test_purchase_data_structure(self, client: TestClient, test_purchase, auth_headers):
        """Тест структуры данных покупки"""
        response = client.get(
            f"/purchases/details/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["purchases"]:
            purchase = data["purchases"][0]
            
            # Проверяем обязательные поля
            required_fields = ["purchased_at", "concert", "amount"]
            for field in required_fields:
                assert field in purchase
            
            # Проверяем структуру концерта
            concert = purchase["concert"]
            concert_fields = ["id", "name", "datetime", "duration", "genre"]
            for field in concert_fields:
                assert field in concert
    
    def test_concert_data_structure(self, client: TestClient, test_purchase, auth_headers):
        """Тест структуры данных концерта"""
        response = client.get(
            f"/purchases/concerts/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["concerts"]:
            concert = data["concerts"][0]
            
            # Проверяем обязательные поля
            required_fields = ["id", "name", "datetime", "duration", "genre"]
            for field in required_fields:
                assert field in concert
            
            # Проверяем структуру зала
            if concert["hall"]:
                hall_fields = ["id", "name", "address"]
                for field in hall_fields:
                    assert field in concert["hall"]
    
    def test_date_format_consistency(self, client: TestClient, test_purchase, auth_headers):
        """Тест консистентности формата дат"""
        response = client.get(
            f"/purchases/details/{test_purchase.external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["purchases"]:
            purchase = data["purchases"][0]
            
            # Проверяем, что даты в формате ISO
            import re
            iso_date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
            
            assert re.match(iso_date_pattern, purchase["purchased_at"])
            assert re.match(iso_date_pattern, purchase["concert"]["datetime"]) 