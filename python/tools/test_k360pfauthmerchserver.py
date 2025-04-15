from fastapi import HTTPException
from k360pfauthmerchserver import build_payload
import pytest

def test_build_payload_success():
    # Arrange
    test_data = {
        "order_id": "123", 
        "device_session_id": "abc123",
        "creation_datetime": "2023-01-01T00:00:00Z",
        "user_ip": "127.0.0.1",
        "account_id": "user123",
        "account_creation_datetime": "2023-01-01T00:00:00Z",
        "items": [
            {
                "price": 10.99,
                "name": "Test Item",
                "quantity": 1
            }
        ]
    }

    # Act
    result = build_payload(test_data)

    # Assert
    assert result["merchantOrderId"] == "123"
    assert result["channel"] == "WEB"  # default value
    assert result["deviceSessionId"] == "abc123"
    assert result["userIp"] == "127.0.0.1"
    assert result["account"]["id"] == "user123"
    assert result["account"]["type"] == "GUEST"  # default value
    assert len(result["items"]) == 1
    assert result["items"][0]["price"] == "10.99"
    assert result["items"][0]["name"] == "Test Item"
    assert result["items"][0]["quantity"] == "1"

def test_build_payload_missing_required_field():
    # Arrange
    incomplete_data = {
        "order_id": "123"
        # Missing required fields
    }

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        build_payload(incomplete_data)
    assert exc_info.value.status_code == 400
    assert "Missing required field" in str(exc_info.value.detail)

def test_build_payload_with_optional_fields():
    # Arrange
    test_data = {
        "order_id": "123",
        "device_session_id": "abc123", 
        "creation_datetime": "2023-01-01T00:00:00Z",
        "user_ip": "127.0.0.1",
        "account_id": "user123",
        "account_creation_datetime": "2023-01-01T00:00:00Z",
        "channel": "MOBILE",
        "username": "testuser",
        "account_type": "REGISTERED",
        "account_is_active": False,
        "items": [
            {
                "price": 10.99,
                "name": "Test Item",
                "quantity": 1,
                "description": "Test Description",
                "category": "Electronics",
                "sub_category": "Phones",
                "is_digital": True,
                "sku": "SKU123",
                "upc": "UPC123",
                "brand": "TestBrand",
                "url": "http://test.com",
                "image_url": "http://test.com/image.jpg"
            }
        ]
    }

    # Act
    result = build_payload(test_data)

    # Assert
    assert result["channel"] == "MOBILE"
    assert result["account"]["username"] == "testuser"
    assert result["account"]["type"] == "REGISTERED"
    assert result["account"]["accountIsActive"] is False
    assert result["items"][0]["description"] == "Test Description"
    assert result["items"][0]["category"] == "Electronics"
    assert result["items"][0]["subCategory"] == "Phones"
    assert result["items"][0]["isDigital"] is True
    assert result["items"][0]["sku"] == "SKU123"
    assert result["items"][0]["brand"] == "TestBrand"
    assert result["items"][0]["url"] == "http://test.com"
    assert result["items"][0]["imageUrl"] == "http://test.com/image.jpg"