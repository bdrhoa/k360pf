# Kount 360 API and webhook example for Laravel

This Laravel 12 application demonstrates three Kount 360 integration flows:

- obtaining and caching an OAuth access token with the client-credentials grant;
- evaluating and updating Payments Fraud orders; and
- receiving a webhook and verifying its RSA-PSS SHA-256 signature before processing the JSON payload.

The token refresh command runs every 15 minutes through Laravel's scheduler. The token service refreshes a cached token when it is missing or within two minutes of expiry and uses a cache lock to prevent concurrent refreshes.

> [!WARNING]
> This is example code, not a production-ready application. It currently writes access tokens, token responses, public-key material, webhook signatures, and raw webhook bodies to the console or logs. Remove or redact those statements before using real credentials or customer data.

## Requirements

- PHP 8.4 or later
- [Composer](https://getcomposer.org/)
- A Kount API credential for the UAT environment
- The base64-encoded DER public key corresponding to the key Kount uses to sign webhooks
- Node.js and npm only if you want to build or serve the starter-page assets

The authentication endpoint is currently fixed to Kount UAT in `app/Services/KountTokenService.php`.

## Installation

From this directory, install the PHP dependencies and create the local environment file:

```sh
composer install
cp .env.example .env
php artisan key:generate
touch database/database.sqlite
php artisan migrate
```

To install and build the optional frontend assets:

```sh
npm install
npm run build
```

Alternatively, `composer run setup` performs the dependency installation, environment-file creation, key generation, database migration, and frontend build in one command. It requires both Composer and npm.

## Configuration

Set these values in `.env`:

```dotenv
KOUNT_API_KEY="base64-encoded-client-credential"
KOUNT_PUBLIC_KEY="base64-encoded-DER-public-key"
KOUNT_CACHE_STORE=file
KOUNT_API_BASE_URL="https://api-sandbox.kount.com"
```

`KOUNT_API_KEY` is passed as the credential portion of the HTTP `Authorization: Basic ...` header when requesting a token. Do not include the literal `Basic ` prefix. `KOUNT_PUBLIC_KEY` must contain the base64 representation of the raw DER public key used to verify webhook signatures.

The Kount token uses Laravel's file-backed cache by default, independently of the application's default cache store. Set `KOUNT_CACHE_STORE` to another configured store, such as `redis`, when appropriate for a multi-instance deployment.

Never commit `.env` or real credentials. After changing environment values in a running or config-cached application, restart the process and clear cached configuration:

```sh
php artisan config:clear
```

## Running the example

Start the local web server:

```sh
php artisan serve
```

The webhook receiver is available at:

```text
POST http://127.0.0.1:8000/api/kount360-webhook-receiver
```

It requires `X-Event-Timestamp` and `X-Event-Signature` headers. The signature must be base64 encoded and must verify over the exact concatenation of the timestamp header and raw request body. Timestamps outside the verifier's five-minute window are rejected.

Kount-specific output is written to daily files under `storage/logs/kount-*.log`.

### Payments Fraud order flow

The Payments Fraud endpoints accept the field names from the Kount Orders API. Both use the existing `KountTokenService`, so outbound requests carry its cached JWT as a bearer token.

See Kount's [Evaluate Order](https://api.kount.com/commerce/help#operation/CommerceOrchestrator_EvaluateOrderRisk), [Update Order](https://api.kount.com/commerce/help#operation/CommerceOrchestrator_UpdateOrder), and [Orders API Best Practices](https://developer.kount.com/hc/en-us/articles/46259173182996-Orders-API-Best-Practices) documentation for the complete contracts and data guidance.

Evaluate a pre-authorization order with:

```sh
curl --request POST \
  --url 'http://127.0.0.1:8000/api/payment-fraud/orders/evaluate' \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --data '{
    "merchantOrderId": "merchant-order-1001",
    "channel": "WEB",
    "deviceSessionId": "device-session-1001",
    "creationDateTime": "2026-09-09T18:30:00Z",
    "userIp": "192.0.2.1",
    "account": {
      "id": "customer-123",
      "creationDateTime": "2024-01-10T10:15:30Z"
    },
    "items": [{
      "id": "item-1",
      "name": "Gaming Mouse",
      "price": "6000",
      "quantity": 1,
      "category": "Electronics"
    }],
    "fulfillment": [{
      "type": "SHIPPED",
      "merchantFulfillmentId": "fulfillment-1001",
      "shipping": {"provider": "UPS", "method": "EXPRESS"}
    }],
    "transactions": [{
      "payment": {
        "type": "CREDIT_CARD",
        "paymentToken": "KHASHED_PAYMENT_VALUE",
        "expirationMonth": 12,
        "expirationYear": 2028
      },
      "orderTotal": "6150",
      "currency": "USD",
      "merchantTransactionId": "merchant-transaction-1001",
      "billedPerson": {
        "name": {"first": "Ada", "family": "Lovelace"},
        "emailAddress": "ada@example.com",
        "address": {
          "line1": "123 Main St",
          "city": "Boise",
          "region": "ID",
          "postalCode": "83702",
          "countryCode": "US"
        }
      }
    }]
  }'
```

Use the `order.orderId` and transaction identifier returned by Kount when sending the real processor result. Do not generate or simulate authorization data in production:

```sh
curl --request PATCH \
  --url 'http://127.0.0.1:8000/api/payment-fraud/orders/KOUNT_ORDER_ID' \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --data '{
    "merchantOrderId": "merchant-order-1001",
    "transactions": [{
      "transactionId": "KOUNT_TRANSACTION_ID",
      "authorizationStatus": {
        "authResult": "APPROVED",
        "processorAuthCode": "001234",
        "processorTransactionId": "PROCESSOR_TRANSACTION_ID",
        "gateway": {"id": "gateway-1", "response": "approved"},
        "verificationResponse": {"cvvStatus": "MATCH", "avsStatus": "Y"}
      }
    }]
  }'
```

If authorization has already happened, include `authorizationStatus` in the initial evaluation instead. Continue using the update endpoint as tracking, fulfillment, refund, or other lifecycle data becomes available.

Only `merchantOrderId` is schema-required for evaluation, so a minimal payload containing that field is forwarded to Kount. For useful model results, follow the Best Practices and send the demonstrated identity, payment, amount, item, billing, and fulfillment fields whenever they have values. Amounts are strings in the currency's lowest denomination. Represent a card with a KHASH `paymentToken` or with both `bin` and `last4`; never send a raw PAN. The device session must match the client-side Device Data Collector session. For call-center or kiosk orders without device collection, add `?excludeDevice=true`. Add `?excludeFromPaymentsModel=true` only for orders that should not train the Payments Fraud model.

Empty strings, nulls, and empty nested objects/arrays are removed before requests reach Kount, while meaningful `false` and zero values are preserved. API failures are returned as errors rather than converted into a fabricated approval decision.

### Refreshing a token

Run one token retrieval or cache check with:

```sh
php artisan kount:refresh-token
```

For a continuous manual exercise of the caching and refresh behavior, use:

```sh
php artisan kount:refresh-token --daemon
```

The daemon checks every 30 seconds and runs until interrupted. Both forms make a live request when no usable token is cached and therefore require a valid `KOUNT_API_KEY` and network access.

### Running the scheduler

For local development, keep this command running in a separate terminal:

```sh
php artisan schedule:work
```

In a deployed environment, arrange for `php artisan schedule:run` to execute once per minute. Laravel will dispatch `kount:refresh-token` every 15 minutes.

## Testing

Install dependencies, then run the automated test suite:

```sh
composer test
```

The suite includes isolated HTTP tests for the Payments Fraud bearer token, query parameters, payload cleanup, URL encoding, validation, and order update flow. It does **not** make a live Kount request or test `KountTokenService`, webhook signature verification, replay-window handling, or webhook response behavior. Passing it should not be treated as end-to-end validation of the Kount integration.

Useful additional checks are:

```sh
composer validate --no-check-publish
./vendor/bin/pint --test
composer audit
```

At the time of this review, Composer validation and the dependency audit pass. The Pint check reports pre-existing style differences in the Kount services, controller, command, logging configuration, and route files.

To confirm the webhook route's required-header validation while the server is running:

```sh
curl -i -X POST \
  -H 'Content-Type: application/json' \
  --data '{"newValue":"APPROVE"}' \
  http://127.0.0.1:8000/api/kount360-webhook-receiver
```

The unsigned request should return HTTP 400 with a missing-timestamp error. A successful end-to-end webhook test requires an authentic Kount-signed payload whose timestamp is within the accepted window. If Kount must reach a local machine, expose the local HTTP server through a trusted HTTPS tunnel and configure the resulting `/api/kount360-webhook-receiver` URL in Kount.
