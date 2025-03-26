"""
JWT-based token utilities for interacting with the Kount API.

This module handles fetching, storing, and refreshing access tokens using
client credentials, along with a singleton TokenManager for in-memory access.

Environment:
    Requires API_KEY to be set as a base64-encoded client credential.
"""

import asyncio
import os
import time
import logging
import jwt
import aiohttp

from fastapi import HTTPException
from tenacity import retry, wait_fixed

# Constants
REFRESH_TIME_BUFFER = 2 * 60  # 2 minutes before expiry
"""
The number of seconds before token expiration to refresh the token.
"""

AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
"""
The URL of the OAuth2 token endpoint for Kount authentication.
"""

API_KEY = os.getenv("API_KEY")
"""
The base64-encoded API key used for authenticating to the Kount auth server.
Must be set as an environment variable named 'API_KEY'.
"""

if not API_KEY:
    raise ValueError("API_KEY environment variable not set.")

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Singleton class to manage the Kount access token in memory.

    Ensures only one instance is created and shared across the application.

    Attributes:
        access_token (str): The current access token (if set).
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TokenManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "access_token"):
            self.access_token = None

    def get_access_token(self):
        """
        Returns the current access token.

        Returns:
            str or None: The stored access token, if any.
        """
        return self.access_token

    def set_access_token(self, token):
        """
        Stores a new access token.

        Args:
            token (str): The new access token to store.
        """
        self.access_token = token


@retry(wait=wait_fixed(10))
async def fetch_or_refresh_token(token_manager: TokenManager):
    """
    Fetches a new access token from the Kount auth server using client credentials.

    Retries every 10 seconds on failure.

    Args:
        token_manager (TokenManager): The token manager instance to update.

    Returns:
        str: The newly obtained access token.

    Raises:
        HTTPException: If the token request fails.
    """
    async with aiohttp.ClientSession() as session:
        try:
            params = {"grant_type": "client_credentials", "scope": "k1_integration_api"}
            headers = {
                "Authorization": f"Basic {API_KEY}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            async with session.post(
                AUTH_SERVER_URL, params=params, headers=headers, timeout=10
            ) as response:
                response.raise_for_status()
                data = await response.json()
                token_manager.set_access_token(data["access_token"])
                logger.info("Token obtained.")
                return data["access_token"]
        except Exception as e:
            logger.error("Failed to fetch token: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to fetch token: {e}") from e


async def start_token_refresh_timer(token_manager: TokenManager):
    """
    Starts a background loop that automatically refreshes the token before it expires.

    Uses the token's decoded expiration time and refreshes it 2 minutes early.

    Args:
        token_manager (TokenManager): The token manager instance to refresh.
    """
    while True:
        current_token = token_manager.get_access_token()
        try:
            decoded = jwt.decode(current_token, options={"verify_signature": False})
            exp_time = decoded["exp"] - REFRESH_TIME_BUFFER
            time_until_refresh = exp_time - int(time.time())
        except jwt.DecodeError:
            time_until_refresh = 0
        if time_until_refresh > 0:
            await asyncio.sleep(time_until_refresh)
        await fetch_or_refresh_token(token_manager)


# Create a global token manager instance to be reused across the app
token_manager = TokenManager()
"""
A global, shared TokenManager instance for use throughout the application.
"""