import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

class TestTicketsAPI:
    """Тесты для API билетов"""
    
    def test_get_tickets_availability_success(self, client: TestClient, test_concert, auth_headers):
        """Тест получения доступности билетов для одного концерта"""
        response = client.get(
            f"/tickets/availability?concert_ids={test_concert.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем структуру ответа
        assert "data" in data
        assert "missing_concerts" in data
        
        # Проверяем, что концерт найден (используем строковый ключ)
        concert_key = str(test_concert.id)
        assert concert_key in data["data"]
        concert_data = data["data"][concert_key]
        assert "available" in concert_data
        assert "concert_id" in concert_data

    def test_get_tickets_availability_multiple_concerts(self, client: TestClient, test_concert, auth_headers, db_session):
        """Тест получения доступности билетов для нескольких концертов"""
        # Создаем второй концерт
        from datetime import datetime, timedelta
        from models.concert import Concert
        
        second_concert = Concert(
            name="Второй тестовый концерт",
            datetime=datetime.now() + timedelta(days=2),
            hall_id=test_concert.hall_id,
            genre="Джаз",
            duration=timedelta(hours=1, minutes=30),
            external_id=12346
        )
        db_session.add(second_concert)
        db_session.commit()
        db_session.refresh(second_concert)
        
        response = client.get(
            f"/tickets/availability?concert_ids={test_concert.id},{second_concert.id}",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что оба концерта найдены
        assert str(test_concert.id) in data["data"]
        assert str(second_concert.id) in data["data"]
        assert len(data["data"]) == 2

    def test_get_tickets_availability_invalid_format(self, client: TestClient):
        """Тест получения информации о билетах с неверным форматом ID"""
        response = client.get("/api/tickets/availability?concert_ids=invalid,format")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Некорректный формат concert_ids" in data["detail"]
    
    def test_get_tickets_availability_empty_list(self, client: TestClient):
        """Тест получения информации о билетах с пустым списком"""
        response = client.get("/api/tickets/availability?concert_ids=")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Список ID концертов пуст" in data["detail"]
    
    def test_get_tickets_availability_nonexistent_concerts(self, client: TestClient, auth_headers):
        """Тест получения доступности билетов для несуществующих концертов"""
        response = client.get(
            "/tickets/availability?concert_ids=99999,99998",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что концерты не найдены
        assert len(data["data"]) == 0
        # Проверяем, что ID в missing_concerts (порядок может быть разным)
        assert len(data["missing_concerts"]) == 2
        assert 99999 in data["missing_concerts"]
        assert 99998 in data["missing_concerts"]

    def test_get_tickets_availability_mixed_concerts(self, client: TestClient, test_concert, auth_headers):
        """Тест получения доступности билетов для смешанного списка концертов"""
        response = client.get(
            f"/tickets/availability?concert_ids={test_concert.id},99999",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что существующий концерт найден
        concert_key = str(test_concert.id)
        assert concert_key in data["data"]
        # Проверяем, что несуществующий концерт в missing_concerts
        assert 99999 in data["missing_concerts"]
    
    def test_get_concert_tickets_availability_success(self, client: TestClient, test_concert):
        """Тест получения информации о доступности билетов для конкретного концерта"""
        response = client.get(f"/api/tickets/availability/{test_concert.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert "data" in data
        assert "timestamp" in data
        
        concert_data = data["data"]
        assert concert_data["concert_id"] == test_concert.id
        assert concert_data["concert_name"] == test_concert.name
        assert "concert_datetime" in concert_data
        assert "available" in concert_data
        assert "tickets_left" in concert_data
        assert "total_seats" in concert_data
        assert "last_updated" in concert_data
        assert "fallback" in concert_data
    
    def test_get_concert_tickets_availability_not_found(self, client: TestClient):
        """Тест получения информации о билетах для несуществующего концерта"""
        response = client.get("/api/tickets/availability/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Концерт с ID 99999 не найден" in data["detail"]
    
    def test_get_tickets_service_status(self, client: TestClient):
        """Тест проверки статуса сервиса билетов"""
        response = client.get("/api/tickets/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["service"] == "tickets_api"
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert data["version"] == "1.0.0"
    
    def test_get_tickets_service_stats(self, client: TestClient):
        """Тест получения статистики сервиса билетов"""
        response = client.get("/api/tickets/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["service"] == "tickets_service"
        assert "cache_stats" in data
        assert "timestamp" in data
        assert isinstance(data["cache_stats"], dict)
    
    def test_update_routes_availability(self, client: TestClient):
        """Тест обновления доступности маршрутов"""
        response = client.post("/api/routes/update-availability")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert "message" in data
        assert "timestamp" in data
    
    def test_tickets_data_structure_consistency(self, client: TestClient, test_concert, auth_headers):
        """Тест консистентности структуры данных билетов"""
        # Первый запрос
        response1 = client.get(
            f"/tickets/availability?concert_ids={test_concert.id}",
            headers=auth_headers
        )
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()["data"][str(test_concert.id)]
        
        # Второй запрос
        response2 = client.get(
            f"/tickets/availability?concert_ids={test_concert.id}",
            headers=auth_headers
        )
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()["data"][str(test_concert.id)]
        
        # Проверяем, что структура одинакова
        assert set(data1.keys()) == set(data2.keys())
        
        # Проверяем обязательные поля
        required_fields = ["available", "concert_id", "concert_name"]
        for field in required_fields:
            assert field in data1
            assert field in data2
    
    def test_tickets_datetime_format(self, client: TestClient, test_concert):
        """Тест формата дат в ответах API билетов"""
        response = client.get(f"/api/tickets/availability/{test_concert.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что даты в формате ISO
        import re
        iso_date_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        
        if data["data"]["concert_datetime"]:
            assert re.match(iso_date_pattern, data["data"]["concert_datetime"])
        
        assert re.match(iso_date_pattern, data["data"]["last_updated"])
        assert re.match(iso_date_pattern, data["timestamp"])
    
    def test_tickets_numeric_fields(self, client: TestClient, test_concert):
        """Тест числовых полей в ответах API билетов"""
        response = client.get(f"/api/tickets/availability/{test_concert.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что числовые поля действительно числа
        assert isinstance(data["data"]["concert_id"], int)
        assert isinstance(data["data"]["tickets_left"], int)
        assert isinstance(data["data"]["total_seats"], int)
        assert isinstance(data["data"]["available"], bool)
        assert isinstance(data["data"]["fallback"], bool)
    
    def test_tickets_error_handling(self, client: TestClient):
        """Тест обработки ошибок в API билетов"""
        # Тестируем различные сценарии ошибок
        test_cases = [
            ("/api/tickets/availability?concert_ids=abc", 400),
            ("/api/tickets/availability?concert_ids=", 400),
            ("/api/tickets/availability/abc", 422),  # FastAPI автоматически валидирует типы
        ]
        
        for url, expected_status in test_cases:
            response = client.get(url)
            assert response.status_code == expected_status
    
    def test_tickets_cache_integration(self, client: TestClient, test_concert):
        """Тест интеграции с кэшем билетов"""
        # Первый запрос
        response1 = client.get(f"/api/tickets/availability/{test_concert.id}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Второй запрос (должен использовать кэш)
        response2 = client.get(f"/api/tickets/availability/{test_concert.id}")
        assert response2.status_code == status.HTTP_200_OK
        
        # Проверяем, что данные консистентны
        data1 = response1.json()["data"]
        data2 = response2.json()["data"]
        
        assert data1["concert_id"] == data2["concert_id"]
        assert data1["concert_name"] == data2["concert_name"] 