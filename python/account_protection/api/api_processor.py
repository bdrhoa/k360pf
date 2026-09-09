"""FastAPI example for the Kount New Account Opening V2 API."""

import asyncio
import json
import logging
import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

import aiohttp
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential

from k360_jwt_auth import token_lifespan
from k360_jwt_auth import token_manager


LOGGER = logging.getLogger(__name__)

KOUNT_API_BASE_URL = os.getenv("KOUNT_API_BASE_URL", "https://api-sandbox.kount.com").rstrip("/")
KOUNT_NAO_API_ENDPOINT = os.getenv(
    "KOUNT_NAO_API_ENDPOINT",
    f"{KOUNT_API_BASE_URL}/newaccountopening/v2",
)
KOUNT_LOGIN_API_ENDPOINT = os.getenv(
    "KOUNT_LOGIN_API_ENDPOINT",
    f"{KOUNT_API_BASE_URL}/login/v2",
)

RETRYABLE_STATUS_CODES = {403, 408, 429, 500, 502, 503, 504}


class KountApiError(Exception):
    """An error response returned by the Kount API."""

    def __init__(
        self,
        status: int,
        response_body: Any,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(f"Kount API returned HTTP {status}")
        self.status = status
        self.response_body = response_body
        self.correlation_id = correlation_id


def build_demo_payload() -> dict[str, Any]:
    """Build the spec-shaped NAO V2 payload used by the Java demo."""

    device_session_id = uuid4().hex
    payload: dict[str, Any] = {
        "inquiryId": uuid4().hex,
        "channel": os.getenv("KOUNT_CHANNEL", "DEFAULT"),
        "deviceSessionId": device_session_id,
        "userIp": "192.168.0.1",
        "accountCreationUrl": "https://www.example.com/create-account",
        "person": {
            "name": {
                "first": "John",
                "last": "Doe",
                "preferred": "Johnny",
            },
            "emailAddress": "john.doe@example.com",
            "phoneNumber": "+12081234567",
            "addresses": [
                {
                    "line1": "5813-5849 Quail Meadows Dr",
                    "line2": "",
                    "city": "Poplar Bluff",
                    "region": "CO",
                    "postalCode": "63901-0000",
                    "countryCode": "USA",
                    "addressType": "BILLING",
                }
            ],
        },
        "account": {
            "id": "11223dr44",
            "type": "VIP",
            "username": "meoyyd8za8jdmwfm",
        },
        "strategy": {
            "verificationTemplateName": "default",
            "verificationTemplateValues": {
                "firstName": "John",
                "accountType": "VIP",
            },
        },
        "customFields": {
            "exampleBoolean": True,
            "exampleNumber": 42,
            "exampleString": "NAO Python demo",
        },
    }

    source_client_id = os.getenv("KOUNT_CLIENT_ID")
    if source_client_id:
        payload["sharedContext"] = {
            "sourceClientId": source_client_id,
            "sourceDeviceSessionId": device_session_id,
        }

    return payload


def build_login_demo_payload() -> dict[str, Any]:
    """Build the spec-shaped Login V2 payload used by the Java demo."""

    return {
        "inquiryId": uuid4().hex,
        "channel": os.getenv("KOUNT_CHANNEL", "DEFAULT"),
        "deviceSessionId": uuid4().hex,
        "userIp": "192.168.0.1",
        "loginUrl": "https://www.example.com/login",
        "person": {
            "name": {
                "first": "John",
                "last": "Doe",
                "preferred": "Johnny",
            },
            "emailAddress": "john.doe@example.com",
            "phoneNumber": "+12081234567",
            "addresses": [
                {
                    "line1": "5813-5849 Quail Meadows Dr",
                    "line2": "",
                    "city": "Poplar Bluff",
                    "region": "CO",
                    "postalCode": "63901-0000",
                    "countryCode": "USA",
                    "addressType": "BILLING",
                }
            ],
        },
        "account": {
            "id": "meoyyd8za8jdmwfm",
            "type": "VIP",
            "creationDateTime": "2024-01-01T12:12:12.000Z",
            "username": "meoyyd8za8jdmwfm",
            "userPassword": "hashedpassword",
            "accountIsActive": True,
        },
        "strategy": {
            "mfaTemplateName": "default",
            "mfaTemplateValues": {
                "firstName": "John",
                "accountType": "VIP",
            },
        },
        "customFields": {
            "exampleBoolean": True,
            "exampleNumber": 42,
            "exampleString": "Login Python demo",
        },
    }


def is_retryable_error(exception: BaseException) -> bool:
    """Return whether an upstream failure is safe to retry."""

    if isinstance(exception, KountApiError):
        return exception.status in RETRYABLE_STATUS_CODES
    return isinstance(
        exception,
        (aiohttp.ClientConnectionError, asyncio.TimeoutError),
    )


def _response_wrapper(body: dict[str, Any], correlation_id: str | None) -> dict[str, Any]:
    """Match the decision wrapper returned by the Java NAO example."""

    decision_value = body.get("decision")
    decision = str(decision_value) if decision_value is not None else None
    normalized_decision = decision.upper() if decision else None
    return {
        "body": body,
        "decision": decision,
        "correlationId": correlation_id,
        "challenge": normalized_decision == "CHALLENGE",
        "allow": normalized_decision == "ALLOW",
        "block": normalized_decision == "BLOCK",
    }


@retry(
    retry=retry_if_exception(is_retryable_error),
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, max=10),
    reraise=True,
)
async def make_kount_api_request(
    session: aiohttp.ClientSession,
    payload: dict[str, Any],
    token_provider: Callable[[], str | None] = token_manager.get_access_token,
    endpoint: str | None = None,
) -> dict[str, Any]:
    """Post an Account Protection inquiry with transient-failure retries."""

    access_token = token_provider()
    if not access_token:
        raise RuntimeError("No Kount access token is available")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    request_endpoint = endpoint or KOUNT_NAO_API_ENDPOINT
    async with session.post(request_endpoint, json=payload, headers=headers) as response:
        response_text = await response.text()
        correlation_id = response.headers.get("X-Correlation-Id")

        try:
            response_body = json.loads(response_text) if response_text else {}
        except json.JSONDecodeError:
            response_body = {"raw": response_text}

        if response.status >= 400:
            raise KountApiError(response.status, response_body, correlation_id)

        if not isinstance(response_body, dict):
            raise KountApiError(
                response.status,
                {"message": "Kount API returned a non-object JSON response"},
                correlation_id,
            )

        return _response_wrapper(response_body, correlation_id)


async def post_new_account_opening(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an HTTP session and submit a New Account Opening inquiry."""

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        return await make_kount_api_request(
            session,
            payload,
            endpoint=KOUNT_NAO_API_ENDPOINT,
        )


async def post_login(payload: dict[str, Any]) -> dict[str, Any]:
    """Create an HTTP session and submit a Login V2 inquiry."""

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        return await make_kount_api_request(
            session,
            payload,
            endpoint=KOUNT_LOGIN_API_ENDPOINT,
        )


app = FastAPI(lifespan=token_lifespan())


@app.post("/demo/nao")
async def send_demo_new_account_opening() -> JSONResponse:
    """Send the demo NAO V2 request and return its decision details."""

    payload = build_demo_payload()
    LOGGER.info("Posting NAO V2 inquiry. inquiryId=%s", payload["inquiryId"])

    try:
        response = await post_new_account_opening(payload)
    except KountApiError as error:
        LOGGER.error(
            "Kount NAO V2 request failed. status=%s correlationId=%s",
            error.status,
            error.correlation_id,
        )
        return JSONResponse(
            status_code=error.status,
            content={
                "error": "Kount API request failed",
                "details": error.response_body,
                "correlationId": error.correlation_id,
            },
        )
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        LOGGER.error("Kount NAO V2 request failed after retries: %s", error)
        return JSONResponse(
            status_code=502,
            content={"error": "Kount API is unavailable after retries"},
        )

    LOGGER.info(
        "Kount NAO V2 request succeeded. inquiryId=%s decision=%s correlationId=%s",
        payload["inquiryId"],
        response["decision"],
        response["correlationId"],
    )
    return JSONResponse(content=response)


@app.post("/demo/login")
async def send_demo_login() -> JSONResponse:
    """Send the demo Login V2 request and return its decision details."""

    payload = build_login_demo_payload()
    LOGGER.info("Posting Login V2 inquiry. inquiryId=%s", payload["inquiryId"])

    try:
        response = await post_login(payload)
    except KountApiError as error:
        LOGGER.error(
            "Kount Login V2 request failed. status=%s correlationId=%s",
            error.status,
            error.correlation_id,
        )
        return JSONResponse(
            status_code=error.status,
            content={
                "error": "Kount API request failed",
                "details": error.response_body,
                "correlationId": error.correlation_id,
            },
        )
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        LOGGER.error("Kount Login V2 request failed after retries: %s", error)
        return JSONResponse(
            status_code=502,
            content={"error": "Kount API is unavailable after retries"},
        )

    LOGGER.info(
        "Kount Login V2 request succeeded. inquiryId=%s decision=%s correlationId=%s",
        payload["inquiryId"],
        response["decision"],
        response["correlationId"],
    )
    return JSONResponse(content=response)
