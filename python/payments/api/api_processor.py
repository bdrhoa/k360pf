#USAGE:
#pip3 install fastapi uvicorn aiohttp pyjwt tenacity "fastapi[standard]""
#uvicorn api_processor:app --reload  // start the server
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
import os
import logging
import json
import random
import asyncio
import aiohttp

from k360_jwt_auth import token_manager
from k360_jwt_auth import token_lifespan

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from tenacity import retry
from tenacity import retry_if_exception
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential
from tenacity import RetryError

# Constants
KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true"
#Use this end point to create a timeout for testing
#KOUNT_API_ENDPOINT = "https://10.255.255.1"  # Non-routable IP (will hang)
# Define possible values for cvvStatus and avsStatus
CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED"]
AVS_STATUSES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", \
    "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

# Credentials (use environment variables or secure vault in production)
API_KEY = os.getenv("KOUNT_API_KEY")

if not API_KEY:
    raise ValueError("KOUNT_API_KEY environment variable not set.")

# Configure logging to write to a file named kount.log
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kount.log"),
        logging.StreamHandler()
    ]
)

def build_payload(incoming_data: dict, patch = False) -> dict:
    """
    Map incoming website data to the Kount API's required payload format.

    Args:
        incoming_data (dict): The raw data from the website.

    Returns:
        dict: A payload formatted for the Kount API.

    Raises:
        ValueError: If the required field `merchantOrderId` is missing.
    """
    merchant_order_id = incoming_data.get("order_id")
    if not merchant_order_id and not patch:
        raise ValueError("Missing required field: merchantOrderId")

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
                "transactionStatus": transaction.get("transaction_status"),
                "authorizationStatus":{
                    "authResult": transaction.get("authorizationStatus", {}).get("authResult"),
                    "dateTime": transaction.get("authorizationStatus", {}).get("dateTime"),
                    "verificationResponse": {
                        "cvvStatus": transaction.get("authorizationStatus", {}).get("verificationResponse", {}).get("cvvStatus"),
                        "avsStatus": transaction.get("authorizationStatus", {}).get("verificationResponse", {}).get("avsStatus"),
                    } if isinstance(transaction.get("authorizationStatus", {}).get("verificationResponse"), dict) else None,
                } if isinstance(transaction.get("authorizationStatus"), dict) else None,
                "merchantTransactionId": transaction.get("merchant_transaction_id"),
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

    return payload

async def handle_api_failure(is_pre_auth: bool, merchant_order_id: str = "UNKNOWN"):
    """
    Handle API failure scenarios by returning a default response.
    
    Args:
        is_pre_auth (bool): Whether the transaction is pre-authorization. Defaults to True.
        merchant_order_id (str): The order ID associated with the transaction. Defaults to "UNKNOWN".

    Returns:
        dict: A default response indicating approval.
    """
    print(is_pre_auth)
    if is_pre_auth:
        simulate_credit_card_authorization(merchant_order_id)

    return {
        "order": {
            "riskInquiry": {
                "decision": "APPROVE"
            }
        }
    }


def is_retryable_error(exception):
    """
    Retry on 403 (Forbidden), 408 (Timeout), 429 (Too Many Requests), or 
            500 (Internal Server Error), 502 (Bad Gateway), 503 (Service Unavailabe)
            or 504 (Gateway Timeout) status codes.
    
        Args:
        exception (Exception): The exception raised during the request.

    Returns:
        bool: True if the exception is an aiohttp.ClientResponseError with a status
            in 403,408,429,500, 502, 503, else False.
    """
    return isinstance(exception, aiohttp.ClientResponseError) and \
        exception.status in {403,408,429,500, 502, 503, 504}

@retry(
    retry=retry_if_exception(is_retryable_error),
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, max=10),  # Adding jitter
)
async def make_kount_api_request(session, payload):
    """
    Make a POST request to the Kount API with retries on HTTP 408 errors.

    This function is decorated with `@retry`, which automatically retries the
    request with exponential backoff if an HTTP 408 (Request Timeout) occurs.

    Args:
        session (aiohttp.ClientSession): The active aiohttp session.
        payload (dict): The formatted payload to send to the Kount API.

    Returns:
        dict: The JSON response from the Kount API.

    Raises:
        HTTPException: If the request fails due to a non-408 error or after all retries.
    """
    headers = {
        "Authorization": f"Bearer {token_manager.get_access_token()}",
        "Content-Type": "application/json",
    }
    try:
        async with session.post(KOUNT_API_ENDPOINT, json=payload, headers=headers) as response:
            if response.status == 400:
                error_details = await response.text()
                logging.error("Kount API Error 400: %s, Payload: %s", error_details, json.dumps(payload))
                return {
                    "error": "Bad Request",
                    "details": error_details,
                    "fallback": True
                }  # Return a fallback error response

            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as e:
        logging.error("Kount API response error: %s", e)
        raise
    except Exception as e:
        logging.error("Unexpected Kount API failure: %s", e)
        raise
async def kount_api_request(payload: dict, is_pre_auth: bool, merchant_order_id: str):
    """
    Wrapper function to handle Kount API requests with retries and error handling.

    If the API request fails after retries, it calls `handle_api_failure()`.

    Args:
        payload (dict): The formatted payload to send to the Kount API.
        is_pre_auth (bool): Whether the transaction is pre-authorization.
        merchant_order_id (str): The merchant order ID.

    Returns:
        dict: The response from the Kount API.
    """
    async with aiohttp.ClientSession() as session:
        try:
            return await make_kount_api_request(session, payload)
        except Exception as e:
            logging.error("Kount API call failed: %s, Payload: %s", e, json.dumps(payload))
            return await handle_api_failure(is_pre_auth, merchant_order_id)
        
# Create the FastAPI app with lifespan handler
#app = FastAPI(lifespan=token_lifespan(use_public_key=False)) // False is default
app = FastAPI(lifespan=token_lifespan())

@app.post("/process-transaction")
async def process_transaction(request: Request):
    """
    Process transaction requests from the client and call the Kount API.

    If any error occurs, return the default fallback response from handle_api_failure().
    """
    is_pre_auth = True  # Always initialized at the beginning
    merchant_order_id = "UNKNOWN"

    try:
        incoming_data = await request.json()
        payload = build_payload(incoming_data)  # May raise ValueError
        merchant_order_id = incoming_data.get("order_id", "UNKNOWN")

        # Ensure transactions exist and extract safely
        transactions = incoming_data.get("transactions", [])
        if isinstance(transactions, list) and transactions:
            first_transaction = transactions[0]
            is_pre_auth = not (
                "authorizationStatus" in first_transaction and "authResult" in first_transaction["authorizationStatus"]
            )

        # Pass is_pre_auth explicitly to kount_api_request
        response = await kount_api_request(payload, is_pre_auth, merchant_order_id)
        decision = response.get("order", {}).get("riskInquiry", {}).get("decision", "UNKNOWN")
        kount_order_id = response.get("order", {}).get("orderId", "UNKNOWN")

        if (
            is_pre_auth
            and kount_order_id != "UNKNOWN"
            and merchant_order_id != "UNKNOWN"
            and decision in {"APPROVE", "REVIEW"}
        ):
            # Schedule the coroutine to run concurrently, without waiting
            asyncio.create_task(safe_patch_credit_card_authorization(kount_order_id, merchant_order_id))

        return JSONResponse(content=response)

    except Exception as e:
        logging.error("Error occurred: %s", e)
        return JSONResponse(content=await handle_api_failure(is_pre_auth, merchant_order_id))
        
def simulate_credit_card_authorization(merchant_order_id: str) -> dict:
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
        "order_id": merchant_order_id,
        "transactions": [
            {
                "authorizationStatus": {
                    "authResult": auth_result,
                    "verificationResponse": {
                        "cvvStatus": cvv_status,
                        "avsStatus": avs_status
                    }
                }
            }
        ]
    }
    return authorization_payload



@retry(
    retry=retry_if_exception(is_retryable_error),  # Retry on 408 and 500 errors
    stop=stop_after_attempt(3),  # Stop after 3 attempts
    wait=wait_random_exponential(multiplier=1, max=10),  # Exponential backoff with jitter
)
async def patch_credit_card_authorization(kount_order_id: str, merchant_order_id: str):
    """
    Posts the simulated credit card authorization payload to the Kount API.

    Args:
        kount_order_id (str): The order ID to associate with the authorization.
        merchant_order_id (str): The merchant order ID.

    Returns:
        dict: The response from the Kount API.
    """
    url = f"https://api-sandbox.kount.com/commerce/v2/orders/{kount_order_id}"
    simulated_auth_data = simulate_credit_card_authorization(merchant_order_id)
    authorization_payload = build_payload(simulated_auth_data, True)
    authorization_payload["transactions"][0]["authorizationStatus"]["authResult"] = "APPROVED"
    
    headers = {
        "Authorization": f"Bearer {token_manager.get_access_token()}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.patch(url, json=authorization_payload, headers=headers) as response:
                response.raise_for_status()  # Raises aiohttp.ClientResponseError if status is 4xx or 5xx
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logging.error("Failed to patch authorization: %s", e)
            raise  # Let Tenacity handle retries

async def safe_patch_credit_card_authorization(kount_order_id: str, merchant_order_id: str):
    """
    Executes the PATCH request to update credit card authorization in the Kount API with retry logic.

    This function wraps `patch_credit_card_authorization()` to handle cases where all retry attempts 
    fail. If retries are exhausted, it extracts the last exception and raises a meaningful HTTP error.

    Args:
        kount_order_id (str): The unique order ID in the Kount system.
        merchant_order_id (str): The merchant's order ID associated with the transaction.

    Returns:
        dict: The successful API response if the request eventually succeeds.

    Raises:
        HTTPException: If all retries fail, raises an error with the final failure details.
    """
    try:
        return await patch_credit_card_authorization(kount_order_id, merchant_order_id)
    except RetryError as re:
        last_exception = re.last_attempt.exception()  # Get the last raised exception
        if isinstance(last_exception, aiohttp.ClientResponseError):
            logging.error("Final failure after retries. Status: %s, URL: %s", last_exception.status, last_exception.request_info.url)
            raise HTTPException(status_code=last_exception.status, detail=f"Final failure after retries: {last_exception.message}")
        else:
            logging.error("Unexpected failure after retries: %s", re)
            raise HTTPException(status_code=500, detail="Unexpected error after retries")