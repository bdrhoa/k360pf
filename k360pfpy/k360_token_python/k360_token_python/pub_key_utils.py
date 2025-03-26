"""
Public key retrieval and refresh utilities for interacting with the Kount ENS API.

This module fetches and refreshes the webhook validation public key.
It uses the existing TokenManager to retrieve the JWT and keeps the key in memory.

Environment:
    Requires the Kount Client ID to be set as an environment variable named 'kount_client_id'.
"""

import asyncio
import os
import time
import logging
import aiohttp
from fastapi import HTTPException
from tenacity import retry, wait_fixed
from .jwt_utils import token_manager, fetch_or_refresh_token

logger = logging.getLogger(__name__)

# Default to sandbox. Override with env var if needed.
KOUNT_USE_SANDBOX = os.getenv("KOUNT_USE_SANDBOX", "true").lower() == "true"

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

    def set_public_key(self, key, valid_until):
        """
        Sets the current public key and its expiration timestamp.

        Args:
            key (str): The public key string.
            valid_until (int): Unix timestamp indicating when the key expires.
        """
        self.public_key = key
        self.valid_until = valid_until

@retry(wait=wait_fixed(10))
async def fetch_public_key():
    """
    Fetches the current ENS public key from the Kount API and stores it in the PublicKeyManager.
    Retries on failure with a fixed delay.

    Raises:
        HTTPException: If the public key cannot be fetched.
    """
    kount_client_id = os.getenv("kount_client_id")
    if not kount_client_id:
        raise ValueError("kount_client_id environment variable not set.")
    
    access_token = token_manager.get_access_token()
    if not access_token:
        access_token = await fetch_or_refresh_token(token_manager)

    url = PUBLIC_KEY_URL_TEMPLATE.format(kount_client_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                valid_until_str = data["validUntil"]
                valid_until_ts = int(time.mktime(time.strptime(valid_until_str, "%Y-%m-%dT%H:%M:%SZ")))
                public_key_manager.set_public_key(data["publicKey"], valid_until_ts)
                logger.info("Public key fetched and stored.")
        except Exception as e:
            logger.error("Failed to fetch public key: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to fetch public key: {e}") from e

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

public_key_manager = PublicKeyManager()
"""
A global, shared PublicKeyManager instance for use throughout the application.
"""