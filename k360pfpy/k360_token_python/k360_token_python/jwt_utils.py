# jwt_utils.py
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
AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("API_KEY environment variable not set.")

logger = logging.getLogger(__name__)

class TokenManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TokenManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "access_token"):
            self.access_token = None

    def get_access_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token


@retry(wait=wait_fixed(10))
async def fetch_or_refresh_token(token_manager: TokenManager):
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


# Create a global token manager instance to be reused
token_manager = TokenManager()
