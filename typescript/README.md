# Kount TypeScript examples

This directory contains the TypeScript examples for Kount APIs and the shared
JWT authentication package used by those examples.

## Directory layout

- `jwt_auth` is the local `@kount/k360-jwt-auth` npm package. Its singleton
  `TokenManager` obtains a client-credentials access token, caches it in memory,
  and refreshes it two minutes before expiration. Tokens are never printed.
- `payments` demonstrates Payment Fraud order inquiries, simulated post-auth
  updates, and Kount webhook-signature verification.
- `payments/api/server-es5.ts` is the older ES5 example and is currently
  independent of the shared JWT package.

The payment example imports `jwt_auth` through a local npm dependency. The
compiled `jwt_auth/dist` output is checked in so a clean install of `payments`
can load the package without first installing the library's development tools.

## Configuration

The payment server requires both variables below at startup:

- `KOUNT_API_KEY`: Base64-encoded `clientId:clientSecret` credentials used for
  OAuth client-credentials authentication.
- `KOUNT_PUBLIC_KEY`: Base64-encoded DER SubjectPublicKeyInfo (SPKI) public key
  used to verify webhook signatures.

Set them in the shell that will run the server:

```bash
export KOUNT_API_KEY='YOUR_BASE64_CLIENT_CREDENTIALS'
export KOUNT_PUBLIC_KEY='YOUR_BASE64_DER_SPKI_PUBLIC_KEY'
```

Do not commit either value or paste the API key into logs, issues, or test
fixtures. 

## Install and build

Build the shared package whenever its source changes:

```bash
cd typescript/jwt_auth
npm ci
npm run build
```

Then install the payment example:

```bash
cd ../payments
npm ci
```

The current `payments` package does not have a working aggregate build or test
script: `npm run build` references missing `api/tsconfig.json` and
`webhook/tsconfig.json` files, while `npm test` is still a placeholder. Use the
focused checks below until those project scripts are replaced.

## Local verification

From `typescript/jwt_auth`:

```bash
npm ci
npm run build
npm audit
```

From `typescript/payments`:

```bash
npm ci
npx tsc --noEmit \
  --target es2016 \
  --module commonjs \
  --strict \
  --esModuleInterop \
  --skipLibCheck \
  api/server.ts
node --check api/server.js
npm audit
```

These checks do not contact Kount. They verify clean dependency installation,
the shared package build, the current TypeScript server, the tracked JavaScript
artifact, and the installed dependency graph.

## Live JWT authentication test

This test contacts the Kount UAT login service and confirms that a non-empty
token is returned without displaying it. Set `KOUNT_API_KEY`, build the package,
and then run from `typescript/jwt_auth`:

```bash
node <<'NODE'
const { TokenManager } = require('./dist');

const manager = TokenManager.getInstance({
  apiKey: process.env.KOUNT_API_KEY,
  logError: message => console.error(message),
});

manager.getAccessToken()
  .then(token => {
    if (!token) throw new Error('No token returned');
    console.log('Live token acquisition passed; token withheld.');
    process.exit(0);
  })
  .catch(error => {
    console.error('Live token acquisition failed:', error.message);
    process.exit(1);
  });
NODE
```

A successful run prints:

```text
Kount access token obtained.
Live token acquisition passed; token withheld.
```

## Live Payment Fraud test

This test contacts both the Kount UAT login service and the Kount sandbox
Commerce API.

In terminal 1, set both required environment variables and start the server:

```bash
cd typescript/payments
npx ts-node api/server.ts
```

In terminal 2, submit a sample pre-auth transaction:

```bash
curl --request POST \
  --url http://127.0.0.1:8000/process-transaction \
  --header 'Content-Type: application/json' \
  --data '{
    "order_id": "12345",
    "transactions": [{
      "processor": "PayPal",
      "payment": {
        "type": "PYPL",
        "payment_token": "TOKEN123"
      },
      "subtotal": "1000",
      "order_total": "1050",
      "currency": "USD"
    }]
  }'
```

Confirm all of the following before treating the run as successful:

1. Terminal 1 prints `Kount access token obtained.`
2. Terminal 1 does not print `Error processing transaction`.
3. The curl response contains the expected Kount order and risk-inquiry data.

The example currently returns a fallback `APPROVE` decision when the Commerce
request fails. Therefore, a curl response containing `APPROVE` by itself is not
proof that the live request succeeded. Review terminal 1 and
`payments/api/kount.log` for errors. Stop the server with **Ctrl+C**.

## Webhook endpoint

The same server exposes `POST /kount360WebhookReceiver`. It requires
`X-Event-Timestamp` and `X-Event-Signature` headers and verifies the signature
against `KOUNT_PUBLIC_KEY` using RSA-PSS with SHA-256. A meaningful live webhook
test must use an authentic Kount delivery or a request signed by the matching
private key; an unsigned curl request should be rejected.
