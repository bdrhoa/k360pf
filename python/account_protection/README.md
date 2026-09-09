# Kount New Account Opening Python example

This FastAPI example obtains and refreshes a Kount bearer token with the shared
`k360_jwt_auth` package, builds a New Account Opening V2 demo inquiry, and posts
it to `/newaccountopening/v2`. Transient HTTP and connection failures are retried
up to three times with exponential backoff and jitter.

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

The example uses `https://api-sandbox.kount.com` by default. Override it with
`KOUNT_API_BASE_URL`, or set `KOUNT_NAO_API_ENDPOINT` to replace the full NAO
endpoint URL (useful for local testing).

## Run the example

From the `python/account_protection` directory:

```bash
python3 -m pip install -r requirements.txt
uvicorn api.api_processor:app --reload
```

Then submit the demo inquiry:

```bash
curl --request POST http://127.0.0.1:8000/demo/nao
```

The successful response wraps the Kount response body, extracted decision,
correlation ID, and convenience flags matching the Java example.

## Run tests

```bash
pytest
```

API reference: [New Account Opening Request V2](https://api.kount.com/newaccountopening/help#operation/NewAccountOpeningService_NewAccountOpeningV2)
