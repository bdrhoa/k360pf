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

import aiohttp
from fastapi import HTTPException
from tenacity import retry, wait_fixed
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .jwt_utils import token_manager, fetch_or_refresh_token

logger = logging.getLogger(__name__)

# Default to sandbox. Override with env var if needed.
KOUNT_USE_SANDBOX = os.getenv("KOUNT_USE_SANDBOX", "true").lower() == "true"

TIMESTAMP_GRACE = datetime.timedelta(minutes=5)

PUBLIC_KEY_URL_TEMPLATE = (
    "https://app-sandbox.kount.com/api/developer/ens/client/{}/public-key"
    if KOUNT_USE_SANDBOX else
    "https://app.kount.com/api/developer/ens/client/{}/public-key"
)

class PublicKeyManager:
    """
    Singleton class to store and manage the current public key and its expiration time.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PublicKeyManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "public_key"):
            self.public_key = None
            self.valid_until = 0

    def get_public_key(self):
        """
        Returns the currently stored public key.
        """
        return self.public_key

    def set_public_key(self, key: str, valid_until: int):
        """
        Sets the current public key and its expiration timestamp.
        """
        self.public_key = key
        self.valid_until = valid_until

public_key_manager = PublicKeyManager()

@retry(wait=wait_fixed(10))
async def fetch_public_key():
    """
    Fetches the current webhook public key from the Kount API and stores it in the PublicKeyManager.
    Falls back to the environment variable KOUNT_PUBLIC_KEY if a 403 or 418 error is received.
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
                              
async def verify_signature(signature_b64: str, timestamp_str: str, payload: bytes) -> bool:
    """
    Verifies a base64-encoded signature against the currently stored public key.
    Includes timestamp grace period check and hashes (timestamp + payload) like the Go implementation.

    Args:
        signature_b64 (str): The base64 encoded signature string from header.
        timestamp_str (str): The ISO8601/RFC3339 formatted timestamp string from header.
        payload (bytes): The raw webhook payload.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """

    # --- Step 1: Check if signature is present ---
    if not signature_b64:
        logger.error("Missing signature.")
        return False

    # --- Step 2: Decode the base64 signature ---
    try:
        signature = base64.b64decode(signature_b64)
    except base64.binascii.Error:
        logger.error("Invalid base64 encoding in signature.")
        return False

    # --- Step 3: Get stored public key (base64 DER encoded, like Go) ---
    public_key_b64 = public_key_manager.get_public_key()
    if not public_key_b64:
        logger.error("Public key not loaded.")
        return False

    # --- Step 4: Decode and load DER-encoded public key ---
    try:
        der_data = base64.b64decode(public_key_b64)
        public_key = serialization.load_der_public_key(der_data)
    except Exception as exc:
        logger.error("Failed to load public key: %s", exc)
        return False

    # --- Step 5: Validate timestamp ---
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        logger.error("Invalid timestamp format: %s", timestamp_str)
        return False

    now = datetime.now(timezone.utc)
    delta = now - timestamp
    if delta > TIMESTAMP_GRACE:
        logger.error("Timestamp too old. Delta: %s", delta)
        return False
    elif delta < -TIMESTAMP_GRACE:
        logger.error("Timestamp too new. Delta: %s", delta)
        return False

    # --- Step 6: Create hash of timestamp + payload ---
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(timestamp_str.encode("utf-8"))
    hasher.update(payload)
    digest = hasher.finalize()

    # --- Step 7: Verify the signature against the hash ---
    try:
        public_key.verify(
            signature,
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        logger.info("Signature successfully verified.")
        return True
    except InvalidSignature:
        logger.error("Signature verification failed.")
        return False
        
async def start_public_key_refresh_timer():
    """
    Starts an asynchronous loop that waits until the public key is near expiry and then refreshes it.
    Runs indefinitely to ensure the public key remains valid.
    """
    while True:
        current_time = int(time.time())
        time_until_refresh = public_key_manager.valid_until - current_time - 120  # 2 minutes buffer
        if time_until_refresh > 0:
            await asyncio.sleep(time_until_refresh)
        await fetch_public_key()