#USAGE:
#pip3 install fastapi uvicorn aiohttp pyjwt "fastapi[standard]""
#uvicorn k360pfauthmerchserver:app --reload  // start the server
#test endpoint: 
'''
curl --request POST \
  --url http://127.0.0.1:8000/process-transaction \
  --header 'Content-Type: application/json' \
  --data '  {
    "order_id": "2025021201",
    "channel": "WEB",
    "device_session_id": "6B29FC40-CA47-1067-B31D-00DD010662DA",
    "creation_datetime": "2025-02-12T15:45:30.123Z",
    "user_ip": "192.168.1.1",
    "account_id": "user-001",
    "account_type": "VIP",
    "account_creation_datetime": "2024-01-10T10:15:30.000Z",
    "username": "testuser",
    "account_is_active": true,
    "items": [
        {
            "price": "1000",
            "description": "High-end gaming mouse",
            "name": "GamerMouseX",
            "quantity": 2,
            "category": "Electronics",
            "sub_category": "Peripherals",
            "is_digital": false,
            "sku": "GMX-2024",
            "upc": "123456789012",
            "brand": "Logitech",
            "url": "https://example.com/gamermousex",
            "image_url": "https://example.com/images/gamermousex.jpg",
            "color": "Black",
            "size": "Medium",
            "weight": "200g",
            "height": "5cm",
            "width": "10cm",
            "depth": "3cm",
            "descriptors": ["ergonomic", "RGB", "wireless"],
            "item_id": "itm-001",
            "is_service": false
        },
        {
            "price": "5000",
            "description": "Annual subscription for software",
            "name": "ProSuite License",
            "quantity": 1,
            "category": "Software",
            "sub_category": "Subscriptions",
            "is_digital": true,
            "sku": "PRO-SUITE-1YR",
            "upc": null,
            "brand": "Adobe",
            "url": "https://example.com/prosuite",
            "image_url": "https://example.com/images/prosuite.jpg",
            "item_id": "itm-002",
            "is_service": false
        }
    ],
    "fulfillment": [
        {
            "type": "SHIPPED",
            "shipping": {
                "amount": "150",
                "provider": "UPS",
                "tracking_number": "1Z9999999999999999",
                "method": "EXPRESS"
            },
            "recipient": {
                "first": "John",
                "family": "Doe",
                "phone_number": "+15551234567",
                "email_address": "john.doe@example.com",
                "address": {
                    "line1": "1234 Elm Street",
                    "line2": "Apt 56",
                    "city": "Los Angeles",
                    "region": "CA",
                    "postal_code": "90001",
                    "country_code": "US"
                }
            },
            "merchant_fulfillment_id": "FULF-001",
            "digital_downloaded": false
        },
        {
            "type": "DIGITAL",
            "accessUrl": "https://downloads.example.com/prosuite",
            "merchant_fulfillment_id": "FULF-002",
            "digital_downloaded": true
        }
    ],
    "transactions": [
        {
            "processor": "PayPal",
            "processor_merchant_id": "MERCH123",
            "payment": {
                "type": "PYPL",
                "payment_token": "TOKEN123456",
                "bin": "411111",
                "last4": "1111"
            },
            "subtotal": "6000",
            "order_total": "6150",
            "currency": "USD",
            "tax": {
                "is_taxable": true,
                "taxable_country_code": "US",
                "tax_amount": "100",
                "out_of_state_tax_amount": "50"
            },
            "billingPerson": {
              "name": {
                "first": "William",
                "preferred": "Bill",
                "family": "Andrade",
                "middle": "Alexander",
                "prefix": "Ms.",
                "suffix": "III"
              },
              "phone": "+15555555555",
              "email": "john.doe@example.com",
              "address": {
                  "line1": "123 Main St",
                  "line2": "Apt 4B",
                  "city": "New York",
                  "region": "NY",
                  "postal_code": "10001",
                  "country_code": "US"
                }
            },
            "merchant_transaction_id": "TXN-789"
        },
        {
            "processor": "Stripe",
            "processor_merchant_id": "STRIPE-987",
            "payment": {
                "type": "CREDIT_CARD",
                "payment_token": "TOKEN654321",
                "bin": "550000",
                "last4": "2222"
            },
            "subtotal": "5000",
            "order_total": "5100",
            "currency": "USD",
            "tax": {
                "is_taxable": true,
                "taxable_country_code": "US",
                "tax_amount": "100"
            },

            "merchant_transaction_id": "TXN-456"
        }
    ],
    "custom_fields": {
        "specialInstruction": "Leave at the front door",
        "giftWrap": true
    }
}'
'''

import io
import logging
import json
import random
import time
import asyncio
import jwt
import aiohttp


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


# Constants
REFRESH_TIME_BUFFER = 2 * 60  # Refresh 2 minutes before expiry
AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true"
# Define possible values for cvvStatus and avsStatus
CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED", "UNKNOWN"]
AVS_STATUSES = ["A", "PARTIAL_MATCH", "NO_MATCH", "UNKNOWN"]

# Credentials (use environment variables or secure vault in production)
#API_KEY = os.getenv("API_KEY")
API_KEY = "MG9hMWJjNXgxcmJrd3ZlM3kzNTg6c3ZHNzZiY19SdGl6c0M1bDJiWGtBeXNyRjRuTkRONGY4YVpqaG9zUkNsTkxoRk94akJ5b3lEQVdvTklkMEU1RA=="

if not API_KEY:
    raise ValueError("API_KEY environment variable not set.")

# Configure logging to write to a file named kount.log
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kount.log"),
        logging.StreamHandler()
    ]
)

class TokenManager:
    """
    Singleton class to manage access tokens for authentication.

    Methods:
        get_access_token: Retrieve the current access token.
        set_access_token: Set a new access token.
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
        Retrieve the current access token.

        Returns:
            str: The current access token.
        """
        return self.access_token

    def set_access_token(self, token):
        """
        Set a new access token.

        Args:
            token (str): The new access token to set.
        """
        self.access_token = token

token_manager = TokenManager()

async def fetch_or_refresh_token():
    """
    Fetch or refresh the JWT token from the authentication server.

    Raises:
        HTTPException: If the token fetch or refresh fails.

    Returns:
        str: The new access token.
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
                print("Token obtained:", token_manager.get_access_token())
                return data["access_token"]
        except Exception as e:
            logging.error("Failed to fetch token: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to fetch token: {e}") from e

async def start_token_refresh_timer():
    """
    Start a background task to refresh the JWT token before it expires.

    The function runs indefinitely, calculating the remaining time until
    the token expires and refreshing it proactively.
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
        await fetch_or_refresh_token()


def build_payload(incoming_data: dict) -> dict:
    """
    Map incoming website data to the Kount API's required payload format.

    Args:
        incoming_data (dict): The raw data from the website.

    Returns:
        dict: A payload formatted for the Kount API.

    Raises:
        HTTPException: If the required field `merchantOrderId` is missing.
    """
    merchant_order_id = incoming_data.get("order_id")
    if not merchant_order_id:
        raise HTTPException(status_code=400, detail="Missing required field: merchantOrderId")

    payload = {
        "merchantOrderId": merchant_order_id,
        "channel": incoming_data.get("channel"),
        "deviceSessionId": incoming_data.get("device_session_id"),
        "creationDateTime": incoming_data.get("creation_datetime"),
        "userIp": incoming_data.get("user_ip"),
        "account": {
            "id": incoming_data.get("account_id"),
            "type": incoming_data.get("account_type"),
            "creationDateTime": incoming_data.get("account_creation_datetime"),
            "username": incoming_data.get("username"),
            "accountIsActive": incoming_data.get("account_is_active"),
        } if isinstance(incoming_data.get("account_id"), (str, int)) else None,
        "items": [
            {
                "price": str(item.get("price", "0")),
                "description": item.get("description"),
                "name": item.get("name"),
                "quantity": item.get("quantity", 1),
                "category": item.get("category"),
                "subCategory": item.get("sub_category"),
                "isDigital": item.get("is_digital"),
                "sku": item.get("sku"),
                "upc": item.get("upc"),
                "brand": item.get("brand"),
                "url": item.get("url"),
                "imageUrl": item.get("image_url"),
                "physicalAttributes": {
                    "color": item.get("color"),
                    "size": item.get("size"),
                    "weight": item.get("weight"),
                    "height": item.get("height"),
                    "width": item.get("width"),
                    "depth": item.get("depth"),
                } if isinstance(item, dict) and any(item.get(k) is not None for k in ["color", "size", "weight", "height", "width", "depth"]) else None,
                "descriptors": item.get("descriptors"),
                "id": item.get("item_id"),
                "isService": item.get("is_service"),
            }
            for item in incoming_data.get("items", []) if isinstance(item, dict)
        ] if "items" in incoming_data else None,
                "fulfillment": [
            {
                "type": fulfillment["type"],
                "shipping": {
                    "amount": str(fulfillment.get("shipping", {}).get("amount", "0")),
                    "provider": fulfillment.get("shipping", {}).get("provider"),
                    "trackingNumber": fulfillment.get("shipping", {}).get("tracking_number"),
                    "method": fulfillment.get("shipping", {}).get("method"),
                },
                "recipientPerson": {
                    "name": {
                        "first": fulfillment["recipient"]["first"],
                        "family": fulfillment["recipient"]["family"],
                    },
                    "phoneNumber": fulfillment["recipient"].get("phone_number"),
                    "emailAddress": fulfillment["recipient"].get("email_address"),
                    "address": fulfillment["recipient"].get("address"),
                } if "recipient" in fulfillment else None,
                "merchantFulfillmentId": fulfillment.get("merchant_fulfillment_id"),
                "digitalDownloaded": fulfillment.get("digital_downloaded"),
            }
            for fulfillment in incoming_data.get("fulfillment", [])
        ] if "fulfillment" in incoming_data else None,
        "transactions": [
            {
                "processor": transaction.get("processor"),
                "processorMerchantId": transaction.get("processor_merchant_id"),
                "payment": {
                    "type": transaction.get("payment", {}).get("type"),
                    "paymentToken": transaction.get("payment", {}).get("payment_token"),
                    "bin": transaction.get("payment", {}).get("bin"),
                    "last4": transaction.get("payment", {}).get("last4"),
                },
                "subtotal": str(transaction.get("subtotal", "0")),
                "orderTotal": str(transaction.get("order_total", "0")),
                "currency": transaction.get("currency"),
                "tax": {
                    "isTaxable": transaction.get("tax", {}).get("is_taxable"),
                    "taxableCountryCode": transaction.get("tax", {}).get("taxable_country_code"),
                    "taxAmount": str(transaction.get("tax", {}).get("tax_amount", "0")),
                    "outOfStateTaxAmount": str(transaction.get("tax", {}).get("out_of_state_tax_amount", "0")),
                },
                "billedPerson": {
                    "name": {
                        "first": transaction.get("billingPerson", {}).get("name", {}).get("first"),
                        "preferred": transaction.get("billingPerson", {}).get("name", {}).get("preferred"),
                        "family": transaction.get("billingPerson", {}).get("name", {}).get("family"),
                        "middle": transaction.get("billingPerson", {}).get("name", {}).get("middle"),
                        "prefix": transaction.get("billingPerson", {}).get("name", {}).get("prefix"),
                        "suffix": transaction.get("billingPerson", {}).get("name", {}).get("suffix"),
                    } if isinstance(transaction.get("billingPerson", {}).get("name"), dict) else None,
                    "phoneNumber": transaction.get("billingPerson", {}).get("phone"),
                    "emailAddress": transaction.get("billingPerson", {}).get("email"),
                    "address": transaction.get("billingPerson", {}).get("address") if isinstance(transaction.get("billingPerson", {}).get("address"), dict) else None,
                } if isinstance(transaction.get("billingPerson"), dict) else None,
                "items": [
                    {
                        "id": item.get("id"),
                        "quantity": item.get("quantity", 1),
                    }
                    for item in transaction.get("items", []) if isinstance(item, dict)
                ],
            }
            for transaction in incoming_data.get("transactions", []) if isinstance(transaction, dict)
        ] if "transactions" in incoming_data else None,
        "customFields": incoming_data.get("custom_fields"),
    }

    # Remove keys where values are None
    payload = {k: v for k, v in payload.items() if v is not None}
    # print("------------")
    # print(json.dumps(payload, indent=4))
    # print("------------")

    return payload

async def kount_api_request(payload: dict):
    """
    Make a POST request to the Kount API with the provided payload.

    Args:
        payload (dict): The formatted payload to send to the Kount API.

    Returns:
        dict: The response from the Kount API.

    Raises:
        HTTPException: If the API call fails or returns an error.
    """
    headers = {
        "Authorization": f"Bearer {token_manager.get_access_token()}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                KOUNT_API_ENDPOINT, json=payload, headers=headers
            ) as response:
                if response.status == 400:
                    error_details = await response.text()
                    logging.error("Kount API Error: %s, Payload: %s", error_details, json.dumps(payload))
                    raise HTTPException(
                        status_code=400, detail=f"Kount API Error: {error_details}"
                    )
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logging.error("Kount API call failed: %s, Payload: %s", e, json.dumps(payload))
            raise HTTPException(status_code=500, detail=f"Kount API call failed: {e}") from e


async def lifespan(application: FastAPI):
    """
    Lifespan context for managing startup and shutdown events.
    """
    # Startup logic
    await fetch_or_refresh_token()
    application.state.refresh_task = asyncio.create_task(start_token_refresh_timer())

    yield  # Yield control for the app's lifespan

    # Shutdown logic
    application.state.refresh_task.cancel()
    try:
        await application.state.refresh_task
    except asyncio.CancelledError:
        pass  # Ignore cancelled error since we are shutting down

# Create the FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)

@app.post("/process-transaction")
async def process_transaction(request: Request):
    """
    Process transaction requests from the client and call the Kount API.

    Args:
        request (Request): The HTTP request containing transaction data.

    Returns:
        JSONResponse: The response from the Kount API.

    Raises:
        HTTPException: If an error occurs during processing or API call.
    """
    try:
        incoming_data = await request.json()
        payload = build_payload(incoming_data)
        response = await kount_api_request(payload)
        decision = response.get("order", {}).get("riskInquiry", {}).get("decision", "UNKNOWN")
        kount_order_id = response.get("order", {}).get("orderId", "UNKNOWN")
        session_id = response.get("order", {}).get("deviceSessionId", "UNKNOWN")
        # Set is_pre_auth based on whether transactions array is empty
        is_pre_auth = True if not response["order"]["transactions"] else False
        is_pre_auth = False
        if (
            is_pre_auth 
            and kount_order_id != "UNKNOWN" 
            and session_id != "UNKNOWN"
            and (decision == "APPROVE" or decision == "REVIEW")
        ):
            # Schedule the coroutine to run concurrently, without waiting
            print("Scheduling patch_credit_card_authorization")
            asyncio.create_task(patch_credit_card_authorization(kount_order_id))        
        return JSONResponse(content=response)
    except HTTPException as e:
        logging.error("HTTPException: %s", e.detail)
        raise e 
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}") from e

def simulate_credit_card_authorization(order_id: str) -> dict:
    """
    Simulates a credit card authorization decision and returns an authorization payload.

    Args:
        order_id (str): The order ID to associate with the authorization.

    Returns:
        dict: The simulated authorization response payload.
    """
    auth_result = random.choice(["APPROVED", "DECLINED"])
    cvv_status = random.choice(CVV_STATUSES)
    avs_status = random.choice(AVS_STATUSES)

    authorization_payload = {
        "orderId": order_id,
        "authorizationStatus": {
            "authResult": auth_result
        },
        "verificationResponse": {
            "cvvStatus": cvv_status,
            "avsStatus": avs_status
        }
    }

    return authorization_payload

async def patch_credit_card_authorization(order_id: str):
    """
    Posts the simulated credit card authorization payload to the Kount API.

    Args:
        order_id (str): The order ID to associate with the authorization.

    Returns:
        dict: The response from the Kount API.
    """
    url = f"https://api-sandbox.kount.com/commerce/v2/orders/{order_id}"
    authorization_payload = simulate_credit_card_authorization(order_id)

    headers = {
        "Authorization": f"Bearer {token_manager.get_access_token()}",
        "Content-Type": "application/json",
    }
    print("Authorization payload:", json.dumps(authorization_payload, indent=4))
    async with aiohttp.ClientSession() as session:
        try:
            async with session.patch(url, json=authorization_payload, headers=headers) as response:
                response.raise_for_status()
                the_repsonse = await response.json()
                print("Authorization response:", the_repsonse)
                return the_repsonse
        except Exception as e:
            logging.error("Failed to post authorization: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to post authorization: {e}") from e