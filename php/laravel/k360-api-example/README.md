# Kount 360 API and webhook example for Laravel

This Laravel 12 application demonstrates two Kount 360 integration flows:

- obtaining and caching an OAuth access token with the client-credentials grant; and
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
```

`KOUNT_API_KEY` is passed as the credential portion of the HTTP `Authorization: Basic ...` header when requesting a token. Do not include the literal `Basic ` prefix. `KOUNT_PUBLIC_KEY` must contain the base64 representation of the raw DER public key used to verify webhook signatures.

The default `.env.example` uses SQLite and Laravel's database-backed cache, queue, and session stores. Run the migrations before invoking the token command so the cache and cache-lock tables exist.

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

The current suite contains only the default Laravel unit assertion and a feature test that checks the home page returns HTTP 200. It does **not** test `KountTokenService`, webhook signature verification, replay-window handling, or webhook response behavior. Passing it should not be treated as validation of the Kount integration.

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
