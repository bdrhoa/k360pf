# k360pf-java

Spring Boot port of the .NET Core Payments Fraud sample. Provides:

- `POST /demo/orders` — sends a demo Orders API request using a client‑credentials bearer token.
- `POST /webhooks/kount360` — receives and verifies RSA‑PSS signed webhooks.

## Configure

Set environment variables (examples for sandbox):

```bash
export K360_AUTH_TOKEN_URL="https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
export K360_API_BASE_URL="https://api-sandbox.kount.com"
export K360_CLIENT_ID="YOUR_CLIENT_ID"
export K360_API_KEY="YOUR_CLIENT_SECRET"
export K360_CHANNEL="default"
# One of the following for webhook verification
export K360_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----
MIIBIjANBgkq...
-----END PUBLIC KEY-----"
# or
export K360_PUBLIC_KEY_URL="https://your-tenant.example/kount360/public-key.pem"
```

## Run

```bash
./mvnw spring-boot:run
# or
mvn -q -DskipTests package && java -jar target/k360pf-java-0.1.0.jar
```

Send a demo order:

```bash
curl -X POST http://localhost:8080/demo/orders
```

Expose Webhook endpoint (dev):

```bash
ngrok http 8080
# Register https://<subdomain>.ngrok.io/webhooks/kount360
```

## Docker

```dockerfile
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY target/k360pf-java-0.1.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
```

Build & run:

```bash
mvn -q -DskipTests package
docker build -t k360pf-java:local .
docker run --rm -p 8080:8080   -e K360_AUTH_TOKEN_URL -e K360_API_BASE_URL   -e K360_CLIENT_ID -e K360_API_KEY   -e K360_PUBLIC_KEY_PEM -e K360_PUBLIC_KEY_URL   k360pf-java:local
```

## Notes

- **Signature headers:** The verifier reads `X-Kount-Signature` or `Signature`. If your tenant uses different names or includes a key ID, update env and `WebhookController`.
- **RSA‑PSS:** SHA‑256, MGF1(SHA‑256), saltLen=32 (adjust if your tenant specifies different params).
- **Payloads:** The demo order uses minimal pseudo fields. Replace with your real `Orders API` contract and a real `deviceSessionId` from your DDC.
