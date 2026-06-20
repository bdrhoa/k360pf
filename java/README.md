# k360pf-java

Spring Boot port of the .NET Core Payments Fraud sample.

## Endpoints

- `POST /demo/orders`
  - Sends a demo Orders API request using a bearer token (client credentials flow)
- `POST /demo/nao`
  - Sends a demo New Account Opening V2 request using a bearer token from `BearerTokenProvider`
- `POST /demo/login`
  - Sends a demo Login V2 decision request using the same bearer token pattern
- `POST /demo/events/failed-attempt`
  - Sends a demo failed-attempt event for login flows
- `POST /demo/events/challenge-outcome`
  - Sends a demo challenge-outcome event for Login or NAO challenge results
- `POST /webhooks/kount360`
  - Receives and verifies RSA-PSS signed webhooks using timestamp + payload

---

# Configuration

The application reads configuration from **environment variables** using Spring Boot property binding.

Use the `KOUNT_` naming convention (recommended):

```bash
export KOUNT_AUTH_TOKEN_URL="https://login-uat.equifax.com/as/token"
export KOUNT_API_BASE_URL="https://api-sandbox.kount.com"
export KOUNT_CLIENT_ID="YOUR_CLIENT_ID"
export KOUNT_API_KEY="YOUR_CLIENT_SECRET"
export KOUNT_CHANNEL="DEFAULT"
export KOUNT_MERCHANT_ID="YOUR_MERCHANT_ID"
export KOUNT_PUBLIC_KEY="<BASE64_DER_PUBLIC_KEY>"
```

## How Spring resolves these

Spring Boot automatically resolves environment variables using `${...}` placeholders in `application.yml`.

Example:

```yaml
kount360:
  api-key: ${KOUNT_API_KEY}
```

At runtime:
- Spring looks for `KOUNT_API_KEY`
- injects it into `Kount360Properties`
- injects that into dependent beans (e.g., `AuthClient`, `OrdersClient`)

---

# Running the App

```bash
mvn clean spring-boot:run
```

App will start on:

```
http://localhost:8080
```

---

# Testing the Orders Flow

## 1. Unit / Integration Test (Java)

Runs the real Kount API:

```bash
mvn -Dtest=OrdersClientLiveTest test
```

This test:
- creates `AuthClient`
- retrieves a real JWT
- calls `/commerce/v2/orders`

---

## 2. Web Endpoint Test

Start the app, then:

```bash
curl -X POST http://localhost:8080/demo/orders
```

Flow:

```
HTTP → OrdersController → OrdersClient → AuthClient → Kount API
```

Expected:
- valid JSON response from Kount
- logs showing JWT usage and request success

---

# Testing the New Account Opening Flow

## 1. Unit / Integration Test (Java)

Runs the real Kount NAO V2 API:

```bash
mvn -Dtest=NAOClientLiveTest test
```

This test:
- creates `AuthClient`
- retrieves a real JWT through `BearerTokenProvider`
- calls `/newaccountopening/v2`

---

## 2. Web Endpoint Test

Start the app, then:

```bash
curl -X POST http://localhost:8080/demo/nao
```

Flow:

```
HTTP → NewAccountOpeningController → NewAccountOpeningClient → AuthClient → Kount NAO V2 API
```

Expected:
- valid JSON response from Kount
- logs showing the NAO inquiry ID, decision, and any response correlation ID

NAO decision responses are returned as:

```json
{
  "body": { "decision": "ALLOW" },
  "decision": "ALLOW",
  "correlationId": null,
  "challenge": false,
  "allow": true,
  "block": false
}
```

When Kount returns `decision: "CHALLENGE"`, preserve the `correlationId` value from the `x-correlation-id` response header. Use that value as `decisionCorrelationId` when posting a later challenge-outcome event.

---

# Testing the Login V2 Flow

## 1. Automated Tests

Run without Kount credentials:

```bash
mvn test
```

Live Kount tests are skipped by default. To opt in, run:

```bash
KOUNT_RUN_LIVE_TESTS=true mvn test
```

To run a single live test:

```bash
KOUNT_RUN_LIVE_TESTS=true mvn -Dtest=NAOClientLiveTest test
```

To run the live Login V2 test:

```bash
KOUNT_RUN_LIVE_TESTS=true mvn -Dtest=LoginV2ClientLiveTest test
```

The live Login V2 tests exercise three policy-driven login URLs:
- `https://www.example.com/login` should return `ALLOW` and simulates login being allowed.
- `https://www.example.com/block` should return `BLOCK` and simulates login not being allowed.
- `https://www.example.com/challenge` should return `CHALLENGE`; challenge handling is currently
  stubbed in the live test.

The client ID associated with `KOUNT_API_KEY` must have policies configured for those URLs;
otherwise the sandbox may return different decisions.

To run the live failed-attempt event test:

```bash
KOUNT_RUN_LIVE_TESTS=true mvn -Dtest=KountEventsClientLiveTest test
```

The Login V2 unit tests use a local mock HTTP server. They verify:
- `POST /login/v2`
- `Authorization: Bearer <token>`
- JSON request fields: `inquiryId`, `channel`, `deviceSessionId`, `userIp`, `loginUrl`, `person`, `account`, `strategy`, `customFields`
- decision parsing for `ALLOW`, `BLOCK`, and `CHALLENGE`
- `x-correlation-id` capture on `CHALLENGE`

## 2. Web Endpoint Test

Start the app, then:

```bash
curl -X POST http://localhost:8080/demo/login
```

Flow:

```
HTTP → LoginV2Controller → LoginV2Client → AuthClient → Kount Login V2 API
```

Expected:
- valid JSON response from Kount
- response wrapper containing the original body, extracted `decision`, and optional `correlationId`

---

# Testing the Events Flow

## 1. Automated Tests

Run without Kount credentials:

```bash
mvn test
```

The Events unit tests use a local mock HTTP server. They verify:
- `POST /events/failed-attempt`
- `POST /events/challenge-outcome`
- bearer token auth
- challenge-outcome JSON includes `decisionCorrelationId`

For real flows, source `decisionCorrelationId` from a prior Login V2 or NAO response where:

```json
{
  "decision": "CHALLENGE",
  "correlationId": "<x-correlation-id response header>"
}
```

## 2. Web Endpoint Tests

Start the app, then:

```bash
curl -X POST http://localhost:8080/demo/events/failed-attempt
```

For challenge outcome, pass the correlation ID returned by a prior `CHALLENGE` decision response:

```bash
curl -X POST http://localhost:8080/demo/events/challenge-outcome \
  -H "Content-Type: application/json" \
  -d '{"decisionCorrelationId":"3438ac3c-37eb-4902-adef-ed16b4431030"}'
```

Flow:

```
HTTP → KountEventsController → KountEventsClient → AuthClient → Kount Events API
```

---

# Testing the Webhook Endpoint

Endpoint:

```bash
POST http://localhost:8080/webhooks/kount360
```

## 1. Basic routing test

```bash
curl -X POST http://localhost:8080/webhooks/kount360
```

Expected:

```
Missing X-Event-Timestamp header
```

---

## 2. Header validation test

```bash
curl -X POST http://localhost:8080/webhooks/kount360 \
  -H "Content-Type: application/json" \
  -H "X-Event-Timestamp: 2026-03-27T21:00:00Z" \
  -H "X-Event-Signature: fake" \
  -d '{"newValue":"APPROVE"}'
```

Expected:
- signature verification failure

---

## 3. Real webhook test

Replay a real webhook:

```bash
curl -X POST http://localhost:8080/webhooks/kount360 \
  -H "Content-Type: application/json" \
  -H "X-Event-Timestamp: <REAL_TIMESTAMP>" \
  -H "X-Event-Signature: <REAL_SIGNATURE>" \
  -d '<REAL_BODY>'
```

---

# Signature Verification Details

The Java implementation matches the .NET version:

- Input:
  - `X-Event-Timestamp`
  - `X-Event-Signature`
  - raw request body

- Digest:

```
timestamp + payload
```

- Algorithm:

```
RSA-PSS (SHA-256)
MGF1(SHA-256)
saltLength = 32
```

- Validation:
  - signature base64 decoding
  - timestamp parsing
  - ±5 minute grace window
  - RSA-PSS verification

---

# Spring Dependency Injection (Autowiring)

Key components:

```java
@Component
class AuthClient

@Component
class OrdersClient

@Component
class SignatureVerifier
```

Spring automatically wires dependencies via constructors:

```java
public OrdersClient(AuthClient auth, Kount360Properties props)
```

Flow:

```
Kount360Properties
        ↓
    AuthClient
        ↓
    OrdersClient
        ↓
 OrdersController
```

No manual instantiation is needed in controllers.

---

# Logging

By default, logs go to the console.

To enable file logging, add to `application.yml`:

```yaml
logging:
  file:
    name: logs/app.log
```

Then:

```bash
tail -f logs/app.log
```

---

# Docker

```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY target/k360pf-java-0.1.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
```

Build and run:

```bash
mvn -q -DskipTests package
docker build -t k360pf-java:local .

docker run --rm -p 8080:8080 \
  -e KOUNT_AUTH_TOKEN_URL \
  -e KOUNT_API_BASE_URL \
  -e KOUNT_CLIENT_ID \
  -e KOUNT_API_KEY \
  -e KOUNT_CHANNEL \
  -e KOUNT_MERCHANT_ID \
  -e KOUNT_PUBLIC_KEY \
  k360pf-java:local
```

---

# Notes

- Use **KOUNT_** variables consistently (recommended)
- Ensure your API key is base64 encoded as required by Kount
- Webhook verification depends on exact byte matching (no whitespace changes)
- Timestamp must be within ±5 minutes
