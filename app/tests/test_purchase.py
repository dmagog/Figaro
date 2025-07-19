import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

class TestPurchaseAPI:
    """Тесты для API покупок"""
    
    def test_get_user_purchased_concerts_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения концертов пользователя"""
        response = client.get(
            f"/purchases/concerts/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_user_purchased_concerts_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения концертов пользователя без аутентификации"""
        response = client.get(f"/purchases/concerts/{test_purchase.user_external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_purchased_concerts_empty(self, client: TestClient, auth_headers):
        """Тест получения концертов для пользователя без покупок"""
        response = client.get("/purchases/concerts/nonexistent_user", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_user_purchases_with_details_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок с деталями"""
        response = client.get(
            f"/purchases/details/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_user_purchases_with_details_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения покупок с деталями без аутентификации"""
        response = client.get(f"/purchases/details/{test_purchase.user_external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_purchases_with_details_empty(self, client: TestClient, auth_headers):
        """Тест получения покупок с деталями для пользователя без покупок"""
        response = client.get("/purchases/details/nonexistent_user", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_user_purchase_count_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения количества покупок пользователя"""
        response = client.get(
            f"/purchases/count/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "count" in data
        assert isinstance(data["count"], int)

    def test_get_user_purchase_count_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения количества покупок без аутентификации"""
        response = client.get(f"/purchases/count/{test_purchase.user_external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_purchase_count_empty(self, client: TestClient, auth_headers):
        """Тест получения количества покупок для пользователя без покупок"""
        response = client.get("/purchases/count/nonexistent_user", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "count" in data
        assert data["count"] == 0

    def test_get_user_purchases_by_date_range_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок по диапазону дат"""
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = client.get(
            f"/purchases/date-range/{test_purchase.user_external_id}",
            params={"start_date": start_date, "end_date": end_date},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_user_purchases_by_date_range_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения покупок по диапазону дат без аутентификации"""
        from datetime import datetime, timedelta
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        response = client.get(
            f"/purchases/date-range/{test_purchase.user_external_id}",
            params={"start_date": start_date, "end_date": end_date}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_purchases_by_date_range_invalid_dates(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок с неверными датами"""
        response = client.get(
            f"/purchases/date-range/{test_purchase.user_external_id}",
            params={"start_date": "invalid-date", "end_date": "invalid-date"},
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_user_purchases_by_date_range_missing_params(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения покупок без параметров дат"""
        response = client.get(
            f"/purchases/date-range/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_user_purchase_summary_success(self, client: TestClient, test_purchase, auth_headers):
        """Тест получения сводки покупок пользователя"""
        response = client.get(
            f"/purchases/summary/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_purchases" in data
        assert "total_spent" in data
        assert "total_concerts" in data

    def test_get_user_purchase_summary_unauthenticated(self, client: TestClient, test_purchase):
        """Тест получения сводки покупок без аутентификации"""
        response = client.get(f"/purchases/summary/{test_purchase.user_external_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_purchase_summary_empty(self, client: TestClient, auth_headers):
        """Тест получения сводки покупок для пользователя без покупок"""
        response = client.get("/purchases/summary/nonexistent_user", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_purchases" in data
        assert data["total_purchases"] == 0

    def test_purchase_data_structure(self, client: TestClient, test_purchase, auth_headers):
        """Тест структуры данных покупки"""
        response = client.get(
            f"/purchases/details/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if len(data) > 0:
            purchase = data[0]
            required_fields = ["id", "user_external_id", "concert_id", "purchased_at", "price"]
            for field in required_fields:
                assert field in purchase

    def test_concert_data_structure(self, client: TestClient, test_purchase, auth_headers):
        """Тест структуры данных концерта"""
        response = client.get(
            f"/purchases/concerts/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if len(data) > 0:
            concert = data[0]
            required_fields = ["id", "name", "datetime", "hall_id"]
            for field in required_fields:
                assert field in concert

    def test_date_format_consistency(self, client: TestClient, test_purchase, auth_headers):
        """Тест консистентности формата дат"""
        response = client.get(
            f"/purchases/details/{test_purchase.user_external_id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if len(data) > 0:
            purchase = data[0]
            if "purchased_at" in purchase:
                # Проверяем, что дата в ISO формате
                from datetime import datetime
                try:
                    datetime.fromisoformat(purchase["purchased_at"].replace("Z", "+00:00"))
                except ValueError:
                    assert False, f"Invalid date format: {purchase['purchased_at']}" 