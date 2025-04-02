"""
FastAPI server for handling Kount360 webhook events.

Instructions:
1. Install dependencies:
   pip install fastapi uvicorn cryptography

2. Run the FastAPI server:
   uvicorn webhook_server:app --host 0.0.0.0 --port 5000
   uvicorn webhook_server:app --reload  # for auto-reload during development

3. Send a POST request with headers:
   - X-Event-Timestamp (ISO8601 format)
   - X-Event-Signature (Base64-encoded signature)

4. Example payload:
   {
       "id": "f276e154-23ef-4366-933b-e1f12e159901",
       "eventType": "Order.StatusChange",
       "apiVersion": "v1",
       "clientId": "900900",
       "kountOrderId": "8V6CFF359HS5QQ6G",
       "merchantOrderId": "qjlm9gvol6olejcs",
       "orderCreationDate": "2022-05-24T23:13:02Z",
       "eventDate": "2022-05-24T23:18:00Z",
       "fieldName": "status",
       "oldValue": "REVIEW",
       "newValue": "DECLINE"
   }

5. Example cURL request:
   curl -X POST "http://localhost:5000/kount360WebhookReceiver" \
        -H "Content-Type: application/json" \
        -H "X-Event-Timestamp: 2022-05-24T23:18:00Z" \
        -H "X-Event-Signature: BASE64_ENCODED_SIGNATURE" \
        -d '{...}'
"""

import json
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from k360_token_python import pub_key_utils
from k360_token_python import token_lifespan
from k360_token_python import InvalidSignatureError
from k360_token_python import TimestampTooOldError
from k360_token_python import TimestampTooNewError
from k360_token_python import MissingPublicKeyError
from k360_token_python import PublicKeyExpiredError

app = FastAPI(lifespan=token_lifespan(use_public_key=True))

# Configure logging
logging.basicConfig(level=logging.INFO)

def simulate_cancel_order():
    """Simulates the cancellation of an order by logging a message."""
    logging.info("Simulated order cancellation")

def simulate_process_order():
    """Simulates processing an order by logging a message."""
    logging.info("Simulated order processing")

@app.post("/kount360WebhookReceiver")
async def kount360_webhook_receiver(request: Request):
    """
    Handles incoming Kount360 webhook events:
    - Extracts headers and body.
    - Verifies the signature and timestamp using pub_key_utils.
    - Processes the webhook according to business logic.
    """

    # Extract headers
    timestamp_header = request.headers.get("X-Event-Timestamp")
    signature_b64 = request.headers.get("X-Event-Signature")

    if not timestamp_header:
        raise HTTPException(status_code=400, detail="Missing X-Event-Timestamp header")
    if not signature_b64:
        raise HTTPException(status_code=400, detail="Missing X-Event-Signature header")

    logging.info("Received X-Event-Timestamp: %s", timestamp_header)

    # Read body
    body = await request.body()
    if not body:
        raise HTTPException(status_code=500, detail="Empty request body")

    # Signature verification with exception handling
    try:
        await pub_key_utils.verify_signature(signature_b64, timestamp_header, body)
    except MissingPublicKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except PublicKeyExpiredError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except InvalidSignatureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimestampTooOldError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimestampTooNewError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Process message
    try:
        payload = json.loads(body)
        new_value = payload.get("newValue")
        if new_value == "DECLINE":
            simulate_cancel_order()
        elif new_value == "APPROVE":
            simulate_process_order()
        else:
            logging.error("Unexpected newValue: %s", new_value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    # Return 200 OK explicitly
    return JSONResponse(content={"status": "ok"}, status_code=200)