"""Tests for the New Account Opening V2 example."""

import asyncio
import json

import pytest
from tenacity import wait_none

from api import api_processor


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status = status
        self._body = json.dumps(body)
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def text(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, *, json, headers):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return self.responses.pop(0)


def test_build_demo_payload_matches_nao_v2_contract(monkeypatch):
    monkeypatch.setenv("KOUNT_CHANNEL", "ACME_WEB")
    monkeypatch.setenv("KOUNT_CLIENT_ID", "900900")

    payload = api_processor.build_demo_payload()

    assert len(payload["inquiryId"]) == 32
    assert set(payload["inquiryId"]) <= set("0123456789abcdef")
    assert "-" not in payload["inquiryId"]
    assert len(payload["deviceSessionId"]) == 32
    assert payload["channel"] == "ACME_WEB"
    assert payload["accountCreationUrl"] == "https://www.example.com/create-account"
    assert payload["person"]["emailAddress"] == "john.doe@example.com"
    assert payload["account"]["id"] == "11223dr44"
    assert payload["strategy"]["verificationTemplateName"] == "default"
    assert payload["sharedContext"] == {
        "sourceClientId": "900900",
        "sourceDeviceSessionId": payload["deviceSessionId"],
    }


def test_build_demo_payload_omits_shared_context_without_client_id(monkeypatch):
    monkeypatch.delenv("KOUNT_CLIENT_ID", raising=False)

    payload = api_processor.build_demo_payload()

    assert "sharedContext" not in payload


def test_build_login_demo_payload_matches_login_v2_contract(monkeypatch):
    monkeypatch.setenv("KOUNT_CHANNEL", "ACME_WEB")

    payload = api_processor.build_login_demo_payload()

    assert len(payload["inquiryId"]) == 32
    assert set(payload["inquiryId"]) <= set("0123456789abcdef")
    assert "-" not in payload["inquiryId"]
    assert len(payload["deviceSessionId"]) == 32
    assert payload["channel"] == "ACME_WEB"
    assert payload["loginUrl"] == "https://www.example.com/login"
    assert payload["person"]["emailAddress"] == "john.doe@example.com"
    assert payload["account"] == {
        "id": "meoyyd8za8jdmwfm",
        "type": "VIP",
        "creationDateTime": "2024-01-01T12:12:12.000Z",
        "username": "meoyyd8za8jdmwfm",
        "userPassword": "hashedpassword",
        "accountIsActive": True,
    }
    assert payload["strategy"]["mfaTemplateName"] == "default"


def test_request_posts_bearer_token_and_preserves_correlation_id(monkeypatch):
    monkeypatch.setattr(
        api_processor,
        "KOUNT_NAO_API_ENDPOINT",
        "https://example.test/newaccountopening/v2",
    )
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"decision": "CHALLENGE"},
                {"X-Correlation-Id": "correlation-123"},
            )
        ]
    )

    response = asyncio.run(
        api_processor.make_kount_api_request(
            session,
            {"inquiryId": "nao-test", "deviceSessionId": "session123"},
            token_provider=lambda: "test-token",
        )
    )

    assert response == {
        "body": {"decision": "CHALLENGE"},
        "decision": "CHALLENGE",
        "correlationId": "correlation-123",
        "challenge": True,
        "allow": False,
        "block": False,
    }
    assert session.requests == [
        {
            "url": "https://example.test/newaccountopening/v2",
            "json": {"inquiryId": "nao-test", "deviceSessionId": "session123"},
            "headers": {
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json",
            },
        }
    ]


def test_request_retries_transient_status(monkeypatch):
    monkeypatch.setattr(
        api_processor,
        "KOUNT_NAO_API_ENDPOINT",
        "https://example.test/newaccountopening/v2",
    )
    session = FakeSession(
        [
            FakeResponse(503, {"error": "unavailable"}),
            FakeResponse(200, {"decision": "ALLOW"}),
        ]
    )
    request_without_wait = api_processor.make_kount_api_request.retry_with(wait=wait_none())

    response = asyncio.run(
        request_without_wait(
            session,
            {"inquiryId": "nao-test", "deviceSessionId": "session123"},
            token_provider=lambda: "test-token",
        )
    )

    assert response["decision"] == "ALLOW"
    assert response["allow"] is True
    assert len(session.requests) == 2


def test_request_does_not_retry_validation_error(monkeypatch):
    monkeypatch.setattr(
        api_processor,
        "KOUNT_NAO_API_ENDPOINT",
        "https://example.test/newaccountopening/v2",
    )
    session = FakeSession(
        [FakeResponse(400, {"error": {"message": "invalid request"}})]
    )
    request_without_wait = api_processor.make_kount_api_request.retry_with(wait=wait_none())

    async def make_request():
        return await request_without_wait(
            session,
            {"inquiryId": "nao-test", "deviceSessionId": "session123"},
            token_provider=lambda: "test-token",
        )

    with pytest.raises(api_processor.KountApiError) as error:
        asyncio.run(make_request())

    assert error.value.status == 400
    assert len(session.requests) == 1


def test_login_request_uses_login_endpoint_and_preserves_correlation_id():
    session = FakeSession(
        [
            FakeResponse(
                200,
                {"decision": "BLOCK"},
                {"X-Correlation-Id": "login-correlation-123"},
            )
        ]
    )

    response = asyncio.run(
        api_processor.make_kount_api_request(
            session,
            {"inquiryId": "login-test", "deviceSessionId": "session123"},
            token_provider=lambda: "test-token",
            endpoint="https://example.test/login/v2",
        )
    )

    assert response["decision"] == "BLOCK"
    assert response["block"] is True
    assert response["correlationId"] == "login-correlation-123"
    assert session.requests[0]["url"] == "https://example.test/login/v2"
