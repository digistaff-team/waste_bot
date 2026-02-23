# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures
"""
import pytest
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_user_seller():
    """Мок данных продавца"""
    return {
        "id": 1,
        "tg_id": 123456789,
        "role": "seller",
        "org_name": "ООО Тест",
        "inn": "7706096338",
        "region": "Москва",
        "phone": "+79001234567",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_user_buyer():
    """Мок данных покупателя"""
    return {
        "id": 2,
        "tg_id": 987654321,
        "role": "buyer",
        "org_name": "ИП Тестов",
        "inn": "500100732259",
        "region": "Московская область",
        "phone": "+79001234567",
        "email": "buyer@example.com",
    }


@pytest.fixture
def mock_user_carrier():
    """Мок данных перевозчика"""
    return {
        "id": 3,
        "tg_id": 111222333,
        "role": "carrier",
        "org_name": "ООО Перевозки",
        "inn": "7714012345",
        "region": "Москва",
        "phone": "+79001234567",
        "email": "carrier@example.com",
        "vehicle_types": "Газель, Фура 20т",
        "capacity": 20.0,
        "carrier_regions": "Москва, Московская область",
    }


@pytest.fixture
def mock_lot():
    """Мок лота"""
    return {
        "id": 1,
        "seller_id": 1,
        "fkko_code": "1 81 010 01 20 5",
        "fkko_name": "Макулатура бумажная",
        "volume": 10.0,
        "unit": "тонна",
        "price": 5000.0,
        "price_format": "за тонну",
        "condition": "с доставкой",
        "address_from": "Москва, ул. Промышленная, 5",
        "address_to": "Москва, ул. Заводская, 10",
        "lat_from": 55.7558,
        "lon_from": 37.6173,
        "lat_to": 55.7558,
        "lon_to": 37.6173,
        "status": "active",
    }


@pytest.fixture
def mock_transport_request():
    """Мок заявки на перевозку"""
    return {
        "id": 1,
        "lot_id": 1,
        "buyer_id": 2,
        "carrier_id": 3,
        "distance_km": 25.5,
        "transport_cost": 3825.0,
        "status": "pending",
    }
