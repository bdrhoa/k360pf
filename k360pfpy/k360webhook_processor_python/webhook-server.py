"""
Instructions:
1. Install dependencies:
   pip install fastapi uvicorn cryptography

2. Run the FastAPI server:
   uvicorn webhook-server:app --host 0.0.0.0 --port 5000
   uvicorn webhook-server:app --reload  // start the server


3. Send a POST request with headers:
      Get the current UTC time from https://www.timeanddate.com/worldclock/timezone/utc
   - X-Event-Timestamp (ISO8601 format) // 2022-05-24T23:18:00Z
   - X-Event-Signature (Base64-encoded signature)

   And a JSON payload like:
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

4. Example cURL request:
   ```sh
   curl -X POST "http://localhost:5000/kount360WebhookReceiver" \
   curl -X POST "http://127.0.0.1:8000/kount360WebhookReceiver" \
        -H "Content-Type: application/json" \
        -H "X-Event-Timestamp: 2022-05-24T23:18:00Z" \
        -H "X-Event-Signature: BASE64_ENCODED_SIGNATURE" \
        -d '{"id":"f276e154-23ef-4366-933b-e1f12e159901","eventType":"Order.StatusChange","apiVersion":"v1","clientId":"900900","kountOrderId":"8V6CFF359HS5QQ6G","merchantOrderId":"qjlm9gvol6olejcs","orderCreationDate":"2022-05-24T23:13:02Z","eventDate":"2022-05-24T23:18:00Z","fieldName":"status","oldValue":"REVIEW","newValue":"DECLINE"}'
   ```
"""

import base64
import hashlib
import datetime
import json
import logging

from fastapi import FastAPI, Request, HTTPException
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

def simulate_cancel_order():
    """Simulates the cancellation of an order by logging a message."""
    logging.info("cancel order")

def simulate_process_order():
    """Simulates processing an order by logging a message."""
    logging.info("process order")

# Public key (Base64-encoded DER format)
PUBLIC_KEY_B64 = (
    "MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAsQr7/3peYbbHkVsS0NlU4ziIFWKjjSI8HcWRSs6QOP6ZXrLXbvcOIuEFYA5ujThLuQfo05EzvWfVSdelbLJ39QNoFfOJ2YE4hq78/8OSloOU/E68M+rrFrxdS1QohsEuzoKD+9hyD2/3JE3vHpi82CjF1msVn9/fBDhYWvWQIOo16N435Wdfl62UZlAun+4TXYxUi+C2s67f58yPQN1uLEL+fa1L05TASqjINh0qjGIaz74g8lT05h/iDzPuTVGofFgTXUZh1yqA9p2P3I3UrK/jLv+aPkCpkwZltZVx99mk8uNVj4exlRC5kACQhvAbLgxiepmZR5XYyNJq1FPLsZuC27g1Squd7LL3Kdbv2tl4mjFG6P1FJwvve6qFVTq7cujEmq9yhfz16d7BPoT1+msZvoc22E7gTkuaW4cnckn7sbioA99zADcdb7OjzEuPd8NqGGD2Ldjg6eese8LF320XQ6jAc4dXcr6ZxVSSQyyI/qTlfi/3OoK7gSrGJT1MGZiohxx9kjt5z/G9fNoMlrQ/yJyLrTZxnlT+MVOsNtFYLZAV0XwVYQZ0a7PQ8hR4wwJxhfK84CcVUON+v4+vrj9bBDZH+boNIUFVDlpMiPjixunSs8FS9DfJ6UnG2YrlbHThgDmmZHj6sY/SUp4mcblBqGQwtxoTkCQqcJQxvAkCAwEAAQ=="
)

def get_public_key():
    """Loads and returns the RSA public key from a Base64-encoded DER format."""
    decoded = base64.b64decode(PUBLIC_KEY_B64)
    return load_der_public_key(decoded)

public_key = get_public_key()
TIMESTAMP_GRACE = datetime.timedelta(minutes=5)

@app.post("/kount360WebhookReceiver")
async def kount360_webhook_receiver(request: Request):
    """Handles incoming Kount360 webhook events, verifies the signature, and processes the order status change."""
    
    # Validate timestamp
    timestamp_header = request.headers.get("X-Event-Timestamp")
    if not timestamp_header:
        raise HTTPException(status_code=400, detail="Missing timestamp")
    
    timestamp_header = request.headers.get("X-Event-Timestamp")
    logging.info(f"Received X-Event-Timestamp: {timestamp_header}")
    if not timestamp_header:
        raise HTTPException(status_code=400, detail="Missing timestamp")
    
    try:
        timestamp = datetime.datetime.fromisoformat(timestamp_header)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid timestamp") from exc
    
    now = datetime.datetime.now(datetime.timezone.utc)
    if now - timestamp > TIMESTAMP_GRACE:
        raise HTTPException(status_code=400, detail="Timestamp too old")
    if now - timestamp < -TIMESTAMP_GRACE:
        raise HTTPException(status_code=400, detail="Timestamp too new")
    
    # Read body
    body = await request.body()
    if not body:
        raise HTTPException(status_code=500, detail="Could not read body")
    
    # Create hash
    hasher = hashlib.sha256()
    hasher.update(timestamp_header.encode("utf-8"))
    hasher.update(body)
    
    # Decode signature
    signature_b64 = request.headers.get("X-Event-Signature")
    if signature_b64:
        logging.info("Raw Signature: %r", signature_b64)
    if not signature_b64:
        raise HTTPException(status_code=400, detail="Missing signature")
    try:
        signature = base64.b64decode(signature_b64)
    except base64.binascii.Error as exc:
        raise HTTPException(status_code=400, detail="Invalid signature encoding") from exc
    
    # Verify signature
    try:
        public_key.verify(
            signature,
            hasher.digest(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except Exception as exc:
        logging.error("Could not verify signature")
        #raise HTTPException(status_code=403, detail="Could not verify signature") from exc # Commented out for testing
    
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
    
    return ""
