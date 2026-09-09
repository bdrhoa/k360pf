# Kount Account Protection Python examples

This FastAPI app demonstrates the Kount Account Protection New Account Opening
V2 and Login V2 APIs. It obtains and refreshes a Kount bearer token with the
shared `k360_jwt_auth` package, builds spec-shaped demo inquiries, and posts them
to `/newaccountopening/v2` and `/login/v2`. Transient HTTP and connection
failures are retried up to three times with exponential backoff and jitter.

The response preserves the `X-Correlation-Id` header so a `CHALLENGE` decision
can be correlated with a later challenge-outcome event.

## Configuration

`KOUNT_API_KEY` is required. It must contain the Base64-encoded
`clientId:clientSecret` value used by the shared JWT authentication package.

```bash
export KOUNT_API_KEY="YOUR_BASE64_ENCODED_CLIENT_CREDENTIALS"
export KOUNT_CLIENT_ID="YOUR_CLIENT_ID"
export KOUNT_CHANNEL="DEFAULT"
```

The examples use `https://api-sandbox.kount.com` by default. Override it with
`KOUNT_API_BASE_URL`, or replace an individual endpoint with
`KOUNT_NAO_API_ENDPOINT` or `KOUNT_LOGIN_API_ENDPOINT` (useful for local testing).

## Run the example

From the `python/account_protection` directory:

```bash
python3 -m pip install -r requirements.txt
uvicorn api.api_processor:app --reload
```

Then submit either demo inquiry:

```bash
curl --request POST http://127.0.0.1:8000/demo/nao
curl --request POST http://127.0.0.1:8000/demo/login
```

The successful response wraps the Kount response body, extracted decision,
correlation ID, and convenience flags matching the Java example.

## Run tests

```bash
pytest
```

API references:

- [New Account Opening Request V2](https://api.kount.com/newaccountopening/help#operation/NewAccountOpeningService_NewAccountOpeningV2)
- [Login Decision Request V2](https://api.kount.com/login/help#operation/LoginService_LoginV2)
