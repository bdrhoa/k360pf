# k360pf-java

Spring Boot port of the .NET Core Payments Fraud sample.

## Endpoints

- `POST /demo/orders`
  - Sends a demo Orders API request using a bearer token (client credentials flow)
- `POST /webhooks/kount360`
  - Receives and verifies RSA-PSS signed webhooks using timestamp + payload

---

# Configuration

The application reads configuration from **environment variables** using Spring Boot property binding.

Use the `KOUNT_` naming convention (recommended):

```bash
export KOUNT_AUTH_TOKEN_URL="https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
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