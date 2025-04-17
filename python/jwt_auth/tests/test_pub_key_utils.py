import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from contextlib import asynccontextmanager
import aiohttp
import gc
import asyncio

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

from k360_token_python import pub_key_utils as pk_utils
from k360_token_python.exceptions import *

# ------------------------
# Fixtures
# ------------------------

@pytest.fixture
def public_key_data():
    return {
        "publicKey": base64.b64encode(b"dummy_public_key").decode(),
        "validUntil": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    }

@pytest.fixture
def mock_aiohttp_success(monkeypatch, public_key_data):
    """Mocks aiohttp.ClientSession to return a 200 success with public key data."""

    # Mock response returned from session.get(...)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=public_key_data)
    mock_response.raise_for_status = Mock()  # sync method, not async

    @asynccontextmanager
    async def mock_get_context_manager(*args, **kwargs):
        yield mock_response

    class MockSession:
        def get(self, *args, **kwargs):
            return mock_get_context_manager()

    @asynccontextmanager
    async def mock_client_session(*args, **kwargs):
        yield MockSession()

    monkeypatch.setattr(aiohttp, "ClientSession", mock_client_session)

@pytest.fixture
def mock_aiohttp_failure(monkeypatch):
    """Mocks aiohttp.ClientSession to return a 403 error response."""

    mock_response = AsyncMock()
    mock_response.status = 403

    @asynccontextmanager
    async def mock_get_context_manager(*args, **kwargs):
        yield mock_response

    class MockSession:
        def get(self, *args, **kwargs):
            return mock_get_context_manager()

    @asynccontextmanager
    async def mock_client_session(*args, **kwargs):
        yield MockSession()

    monkeypatch.setattr(aiohttp, "ClientSession", mock_client_session)

# ------------------------
# PublicKeyManager tests
# ------------------------

def test_public_key_manager_singleton():
    manager1 = pk_utils.PublicKeyManager()
    manager2 = pk_utils.PublicKeyManager()
    assert manager1 is manager2

def test_public_key_manager_set_and_get():
    manager = pk_utils.PublicKeyManager()
    manager.set_public_key("fake_key", 1234567890)
    assert manager.get_public_key() == "fake_key"
    assert manager.valid_until == 1234567890

# ------------------------
# fetch_public_key tests
# ------------------------

@pytest.mark.asyncio
async def test_fetch_public_key_success(monkeypatch, mock_aiohttp_success, public_key_data):
    monkeypatch.setenv("KOUNT_CLIENT_ID", "dummy_id")
    monkeypatch.setattr(pk_utils.token_manager, "get_access_token", lambda: "dummy_token")
    monkeypatch.setattr(pk_utils, "fetch_or_refresh_token", lambda _: "dummy_token")

    await pk_utils.fetch_public_key()

    assert pk_utils.public_key_manager.get_public_key() == public_key_data["publicKey"]

@pytest.mark.asyncio
async def test_fetch_public_key_fallback(monkeypatch, mock_aiohttp_failure):
    monkeypatch.setenv("KOUNT_CLIENT_ID", "dummy_id")
    monkeypatch.setenv("KOUNT_PUBLIC_KEY", "fallback_key")
    monkeypatch.setattr(pk_utils.token_manager, "get_access_token", lambda: "dummy_token")

    await pk_utils.fetch_public_key()
    assert pk_utils.public_key_manager.get_public_key() == "fallback_key"

# @pytest.mark.asyncio
# async def test_fetch_public_key_no_env(monkeypatch, mock_aiohttp_failure):
#     """Ensure that missing env var triggers ValueError and cleans up coroutines."""
#     monkeypatch.delenv("KOUNT_CLIENT_ID", raising=False)

#     with pytest.raises(ValueError, match="kount_client_id environment variable not set."):
#         await pk_utils.fetch_public_key()

#     # Force event loop to clean up lingering coroutines
#     await asyncio.sleep(0)
#     gc.collect()
            
    # Define a minimal dummy session to avoid hanging
    class DummySession:
        def get(self, *args, **kwargs):
            @asynccontextmanager
            async def dummy_get():
                yield None
            return dummy_get()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    @asynccontextmanager
    async def dummy_client_session(*args, **kwargs):
        yield DummySession()

    monkeypatch.setattr(aiohttp, "ClientSession", dummy_client_session)

    with pytest.raises(ValueError, match="kount_client_id environment variable not set."):
        await pk_utils.fetch_public_key()

# ------------------------
# verify_signature tests
# ------------------------

@pytest.mark.asyncio
async def test_verify_signature_success():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key_b64 = base64.b64encode(public_key_der).decode()

    pk_utils.public_key_manager.set_public_key(
        public_key_b64,
        int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    payload = b"test_payload"

    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(timestamp.encode("utf-8"))
    hasher.update(payload)
    digest = hasher.finalize()

    signature = private_key.sign(
        digest,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode()

    assert await pk_utils.verify_signature(signature_b64, timestamp, payload) is True

@pytest.mark.asyncio
@pytest.mark.parametrize("sig", ["", "!!!"])
async def test_verify_signature_invalid_base64(sig):
    with pytest.raises(InvalidSignatureError):
        await pk_utils.verify_signature(sig, datetime.now(timezone.utc).isoformat(), b"payload")

@pytest.mark.asyncio
async def test_verify_signature_missing_key():
    pk_utils.public_key_manager.set_public_key(None, 0)
    with pytest.raises(MissingPublicKeyError):
        await pk_utils.verify_signature("dummy", datetime.now(timezone.utc).isoformat(), b"payload")

@pytest.mark.asyncio
async def test_verify_signature_expired_key():
    pk_utils.public_key_manager.set_public_key(
        "dGVzdA==",
        int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp())
    )
    with pytest.raises(PublicKeyExpiredError):
        await pk_utils.verify_signature("dummy", datetime.now(timezone.utc).isoformat(), b"payload")

@pytest.mark.asyncio
async def test_verify_signature_timestamp_too_old():
    pk_utils.public_key_manager.set_public_key(
        "dGVzdA==",
        int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
    )
    old_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with pytest.raises(TimestampTooOldError):
        await pk_utils.verify_signature("dummy", old_time, b"payload")

@pytest.mark.asyncio
async def test_verify_signature_timestamp_too_new():
    pk_utils.public_key_manager.set_public_key(
        "dGVzdA==",
        int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
    )
    future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    with pytest.raises(TimestampTooNewError):
        await pk_utils.verify_signature("dummy", future_time, b"payload")