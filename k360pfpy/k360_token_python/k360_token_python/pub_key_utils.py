"""
Public key retrieval and refresh utilities for interacting with the Kount ENS API.

This module fetches and refreshes the webhook validation public key.
It uses the existing TokenManager to retrieve the JWT and keeps the key in memory.

Environment:
    Requires the Kount Client ID to be set as an environment variable named 'kount_client_id'.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import os
import time
import logging
import base64
from typing import Optional

import aiohttp
from fastapi import HTTPException
from tenacity import retry, wait_fixed
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .jwt_utils import token_manager, fetch_or_refresh_token

from .exceptions import (
    InvalidSignatureError,
    TimestampTooOldError,
    TimestampTooNewError,
    MissingPublicKeyError,
    PublicKeyExpiredError
)


logger = logging.getLogger(__name__)

# Default to sandbox. Override with env var if needed.
KOUNT_USE_SANDBOX = os.getenv("KOUNT_USE_SANDBOX", "true").lower() == "true"

PUBLIC_KEY_URL_TEMPLATE = (
    "https://app-sandbox.kount.com/api/developer/ens/client/{}/public-key"
    if KOUNT_USE_SANDBOX else
    "https://app.kount.com/api/developer/ens/client/{}/public-key"
)


# ---------------------------
# Public Key Manager
# ---------------------------

class PublicKeyManager:
    """
    Singleton class to store and manage the current public key and its expiration time.

    Attributes:
        public_key (str): The currently loaded public key as a base64-encoded string.
        valid_until (int): The UNIX timestamp indicating when the public key expires.
    """
    _instance: Optional["PublicKeyManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # initialize the attributes on instance creation, not in __init__
            cls._instance.public_key = None
            cls._instance.valid_until = 0
        return cls._instance

    def get_public_key(self) -> Optional[str]:
        """
        Returns the currently stored public key.

        Returns:
            Optional[str]: The base64-encoded public key or None if not loaded.
        """
        return self.public_key

    def set_public_key(self, key: str, valid_until: int):
        """
        Sets the current public key and its expiration timestamp.

        Args:
            key (str): The base64-encoded public key.
            valid_until (int): The UNIX timestamp when the key expires.
        """
        self.public_key = key
        self.valid_until = valid_until
        
    def reset(self):
        """Reset public key state."""
        self.public_key = None
        self.valid_until = 0

public_key_manager = PublicKeyManager()

# ---------------------------
# Fetch Public Key
# ---------------------------

@retry(wait=wait_fixed(10))
async def fetch_public_key():
    """
    Fetches the current webhook public key from the Kount ENS API and stores it in the PublicKeyManager.

    If a 403 or 418 is returned, falls back to using the KOUNT_PUBLIC_KEY environment variable.

    Raises:
        HTTPException: If public key cannot be fetched or fallback is missing.
    """
    kount_client_id = os.getenv("KOUNT_CLIENT_ID")
    if not kount_client_id:
        raise ValueError("kount_client_id environment variable not set.")

    access_token = token_manager.get_access_token() or await fetch_or_refresh_token(token_manager)

    url = PUBLIC_KEY_URL_TEMPLATE.format(kount_client_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status in (403, 418):
                    fallback_key = os.getenv("KOUNT_PUBLIC_KEY")
                    if not fallback_key:
                        raise HTTPException(status_code=response.status, detail=f"Received {response.status} from Kount API and no fallback public key found.")
        
                    valid_until_dt = datetime.now(timezone.utc) + timedelta(days=365)
                    valid_until_ts = int(valid_until_dt.timestamp())
                    public_key_manager.set_public_key(fallback_key, valid_until_ts)
                    logger.warning("Using fallback public key from environment variable due to %s error.", response.status)
                    return

                response.raise_for_status()
                data = await response.json()
                valid_until_str = data["validUntil"]
                valid_until_dt = datetime.strptime(valid_until_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                valid_until_ts = int(valid_until_dt.timestamp())

                public_key_manager.set_public_key(data["publicKey"], valid_until_ts)
                logger.info("Public key fetched and stored.")

        except Exception as e:
            logger.error("Failed to fetch public key: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to fetch public key: {e}") from e

# ---------------------------
# Signature Verification
# ---------------------------

async def verify_signature(signature_b64: str, timestamp_str: str, payload: bytes, grace: timedelta = timedelta(minutes=5), now: Optional[datetime] = None) -> bool:
    """
    Verifies a base64-encoded signature against the currently stored public key.

    This includes:
    - Decoding the signature.
    - Checking public key presence and expiration.
    - Checking timestamp validity.
    - Hashing timestamp + payload.
    - Verifying the RSA PKCS1v15 signature.

    Args:
        signature_b64 (str): Base64 encoded signature from header.
        timestamp_str (str): ISO8601/RFC3339 formatted timestamp from header.
        payload (bytes): Raw webhook payload.
        grace (timedelta): Allowed clock skew (default 5 minutes).
        now (Optional[datetime]): Inject current time for testing.

    Raises:
        MissingPublicKeyError: If no public key is available.
        PublicKeyExpiredError: If the stored public key is expired.
        InvalidSignatureError: If the signature is invalid or can't be decoded.
        TimestampTooOldError: If the timestamp is too old.
        TimestampTooNewError: If the timestamp is too new.

    Returns:
        bool: True if the signature is valid.
    """
    if not signature_b64:
        logger.error("Missing signature.")
        raise InvalidSignatureError("Missing signature.")

    # Decode signature
    try:
        signature = base64.b64decode(signature_b64)
    except base64.binascii.Error as exc:
        logger.error("Invalid base64 encoding in signature.")
        raise InvalidSignatureError("Invalid base64 encoding in signature.") from exc

    # Get stored public key
    public_key_b64 = public_key_manager.get_public_key()
    if not public_key_b64:
        logger.error("Public key not loaded.")
        raise MissingPublicKeyError("Public key not loaded.")

    # Check if public key is expired
    if public_key_manager.valid_until and datetime.now(timezone.utc).timestamp() > public_key_manager.valid_until:
        logger.error("Public key expired.")
        raise PublicKeyExpiredError("Public key expired.")

    # Load public key
    try:
        der_data = base64.b64decode(public_key_b64)
        public_key = serialization.load_der_public_key(der_data)
    except Exception as exc:
        logger.error("Failed to load public key: %s", exc)
        raise InvalidSignatureError("Failed to load public key.") from exc

    # Validate timestamp
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError as exc:
        logger.error("Invalid timestamp format: %s", timestamp_str)
        raise InvalidSignatureError("Invalid timestamp format.") from exc

    now = now or datetime.now(timezone.utc)
    delta = now - timestamp
    if delta > grace:
        logger.error("Timestamp too old. Delta: %s", delta)
        raise TimestampTooOldError("Timestamp too old.")
    elif delta < -grace:
        logger.error("Timestamp too new. Delta: %s", delta)
        raise TimestampTooNewError("Timestamp too new.")

    # Hash timestamp + payload
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(timestamp_str.encode("utf-8"))
    hasher.update(payload)
    digest = hasher.finalize()

    # Verify signature
    try:
        public_key.verify(
            signature,
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        logger.info("Signature successfully verified.")
        return True
    except InvalidSignature as exc:
        logger.error("Signature verification failed.")
        raise InvalidSignatureError("Signature verification failed.") from exc

# ---------------------------
# Refresh Timer
# ---------------------------

async def start_public_key_refresh_timer():
    """
    Starts an asynchronous background task to refresh the public key when near expiry.

    Waits until 2 minutes before expiration, then refreshes the key.
    """
    while True:
        current_time = int(time.time())
        time_until_refresh = public_key_manager.valid_until - current_time - 120  # 2 minutes buffer
        if time_until_refresh > 0:
            await asyncio.sleep(time_until_refresh)
        await fetch_public_key()
