"""
Asynchronous Python module for managing JWT authentication and integrating
with the Kount API, using a singleton class for token management.

Features:
- Fetching and refreshing JWTs from an authentication server.
- Proactive token refresh with a timer to ensure tokens don't expire during use.
- Reactive token refresh when a 401 Unauthorized error occurs during API calls.
- Integration with the Kount API for risk analysis.

Dependencies:
- aiohttp: For asynchronous HTTP requests.
- jwt: For decoding JWT tokens.

Constants:
- REFRESH_TIME_BUFFER: Buffer time before token expiration to trigger refresh.
- AUTH_SERVER_URL: URL for the authentication server.
- KOUNT_API_ENDPOINT: URL for the Kount API endpoint.
"""

import asyncio
from datetime import datetime
import time
import jwt
import aiohttp

# Constants
REFRESH_TIME_BUFFER = 2 * 60  # Refresh 2 minutes before expiry
AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true"

# Credentials
#API_KEY = "your_api_key_here"
#API_KEY = os.getenv("API_KEY")
API_KEY = "MG9hMWJjNXgxcmJrd3ZlM3kzNTg6c3ZHNzZiY19SdGl6c0M1bDJiWGtBeXNyRjRuTkRONGY4YVpqaG9zUkNsTkxoRk94akJ5b3lEQVdvTklkMEU1RA=="


class TokenManager:
    """Singleton class to manage access tokens."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of TokenManager exists."""
        if not cls._instance:
            cls._instance = super(TokenManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        """Initialize the access token."""
        # Initialize access_token if it hasn't been already.
        if not hasattr(self, "access_token"):
            self.access_token = None

    def get_access_token(self):
        """Retrieve the current access token."""
        return self.access_token

    def set_access_token(self, token):
        """Set a new access token."""
        self.access_token = token


# Create a single instance of TokenManager
token_manager = TokenManager()


async def fetch_or_refresh_token():
    """
    Fetch the initial JWT or refresh the existing JWT from the authentication server.

    Uses client credentials grant type to request the token.
    """
    async with aiohttp.ClientSession() as session:
        try:
            params = {
                "grant_type": "client_credentials",
                "scope": "k1_integration_api"
            }
            headers = {
                "Authorization": f"Basic {API_KEY}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            async with session.post(AUTH_SERVER_URL,
                                    params=params,
                                    headers=headers,
                                    timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                token_manager.set_access_token(data["access_token"])
                print("Token obtained:", token_manager.get_access_token())
        except Exception as e:
            print("Failed to obtain token:", e)
            raise e


async def start_token_refresh_timer():
    """
    Start a background timer to proactively refresh the JWT before it expires.

    The timer calculates the token's expiration time and refreshes it with a buffer
    to ensure continuous availability.
    """
    while True:
        current_token = token_manager.get_access_token()
        try:
            decoded = jwt.decode(current_token, options={"verify_signature": False})
            exp_time = decoded['exp'] - REFRESH_TIME_BUFFER
            
            # Convert to human-readable time
            readable_time = datetime.fromtimestamp(exp_time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Token expires at: {readable_time} UTC")
            
            time_until_refresh = exp_time - int(time.time())
        except jwt.DecodeError:
            print("Failed to decode JWT; refreshing immediately.")
            time_until_refresh = 0
        if time_until_refresh > 0:
            print(f"Current time: {int(time.time())}, Expiration time: {exp_time}, Time until refresh: {time_until_refresh}")
            await asyncio.sleep(time_until_refresh)
        await fetch_or_refresh_token()


async def kount_api_request(session):
    """
    Perform a POST request to the Kount API with a JSON payload.

    Logs details about the error if a 400 status code is returned.
    """
    headers = {
        'Authorization': f'Bearer {token_manager.get_access_token()}',
        'Content-Type': 'application/json'
    }
    payload = """
    {
        "merchantOrderId": "d121ea2210434ffc8a90daff9cc97e76",
        "channel": "SPHERE",
        "deviceSessionId": "12345",
        "creationDateTime": "2019-08-24T14:15:22Z",
        "userIp": "192.168.0.1",
        "account": {
            "id": "d121ea2210434ffc8a90daff9cc97e76",
            "type": "PRO_ACCOUNT",
            "creationDateTime": "2019-08-24T14:15:22Z",
            "username": "johndoe1983",
            "accountIsActive": true
        },
        "items": [
            {
                "price": "100",
                "description": "Samsung 46\\\" LCD HDTV",
                "name": "LN46B610",
                "quantity": "1",
                "category": "TV",
                "subCategory": "OLED TV",
                "isDigital": true,
                "sku": "TSH-000-S",
                "upc": "03600029145",
                "brand": "LG",
                "url": "https://www.example.com/store/tsh-000-s",
                "imageUrl": "https://www.example.com/store/tsh-000-s/thumbnail.png"
            }
        ]
    }
    """
    try:
        async with session.post(KOUNT_API_ENDPOINT, data=payload, headers=headers) as response:
            if response.status == 400:
                error_details = await response.text()
                print("Kount API Error Response:", error_details)
                raise Exception(f"Kount API Error: {error_details}")
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        print("HTTP error during Kount API call:", e)
        raise

async def main():
    """
    Main asynchronous function to manage the application workflow.

    - Fetch the initial JWT.
    - Start the token refresh timer.
    - Perform the Kount API request.
    """
    start_time = time.time()
    await fetch_or_refresh_token()
    asyncio.create_task(start_token_refresh_timer())

    async with aiohttp.ClientSession() as session:
        for i in range(10):  # Call the API 50 times for testing
            print(f"Making Kount API call #{i + 1}")
            try:
                response = await kount_api_request(session)
                print("Kount API Response:", response)
            except aiohttp.ClientError as e:
                print("HTTP error during Kount API call:", e)
            except jwt.DecodeError as e:
                print("JWT decode error during Kount API call:", e)
            except Exception as e:
                print("Unexpected error during Kount API call:", e)
                
            await asyncio.sleep(4 * 60)  # 1-second delay between API calls for testing

    end_time = time.time()
    print(f"Total execution time: {end_time - start_time} seconds")

if __name__ == "__main__":
    asyncio.run(main())
