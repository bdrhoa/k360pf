# Kount360 API & Webhook Laravel Integration

This project is a Laravel 11 application demonstrating a robust, enterprise-grade integration with the Kount360 API. It features secure JWT authentication, proactive token caching, and an RSA-PSS signed webhook receiver.

## Features
* **Proactive JWT Caching:** Background worker ensures API tokens are always fresh and ready in memory.
* **Resilient API Communication:** Built-in exponential backoff and jitter for handling network blips or rate limits.
* **Secure Webhooks:** Utilizes `phpseclib` to verify incoming Kount webhooks against strict RSA-PSS cryptographic signatures.
* **Dedicated Logging:** All Kount-related events (token refreshes, webhook payloads, crypto failures) are isolated in `storage/logs/kount-YYYY-MM-DD.log`.

---

## ⚙️ Configuration & Environment Variables

This application requires two primary Kount credentials:
1. `KOUNT_API_KEY`: The base64-encoded string used for Basic Auth to generate your JWT.
2. `KOUNT_PUBLIC_KEY`: The base64-encoded raw DER public key used to verify incoming webhook signatures.

You can configure these in one of two ways:

### Option A: The Project `.env` File (Standard)
Copy the `.env.example` file to `.env` and add your keys to the bottom. This is the standard approach for isolated applications.

    KOUNT_API_KEY=your_base64_api_key_here
    KOUNT_PUBLIC_KEY=your_base64_public_key_here

### Option B: System-Level Variables (Advanced/Shared)
If you are running multiple applications on the same server (e.g., sharing these keys with a Symfony demo), you can export them directly in your system's shell profile (like `~/.zshenv` or `~/.bash_profile`). 

    export KOUNT_API_KEY="your_base64_api_key_here"
    export KOUNT_PUBLIC_KEY="your_base64_public_key_here"

*Note: Laravel will automatically inherit system-level environment variables. If a variable exists at the system level, it will override whatever is written in the local `.env` file. You must restart your PHP server (`php artisan serve`) after updating system variables.*

---

## 🔐 Authentication & JWT Caching Explained

Kount issues JSON Web Tokens (JWTs) that expire after 20 minutes. Instead of fetching a new token on every single web request (which adds massive latency), this application utilizes a **Proactive Caching Strategy**.

The `KountTokenService` stores the active JWT in Laravel's Cache. When your application needs to talk to Kount, it instantly pulls the token from memory. 

To prevent the token from ever expiring, a scheduled Artisan command (`kount:refresh-token`) runs in the background. 
* It checks the cache every 15 minutes.
* If the token is nearing expiration, it uses an atomic cache lock to ensure only one process reaches out to Kount.
* It securely fetches a new token, updates the cache, and logs the rotation.

---

## ⏱️ Setting Up the Background Job (Token Refresh)

To keep the JWT cache warm, you must tell Laravel to execute its Task Scheduler. How you do this depends on your environment.

### Local & Testing Environments
When developing on your local machine, you do not need to configure a system-level cron job. Laravel provides a dedicated worker command that stays alive in your terminal and executes tasks as they come due.

Open a dedicated terminal tab, navigate to the project root, and run:

    php artisan schedule:work

*Leave this tab running in the background. It will automatically fire the refresh command every 15 minutes.*

### Production Environments
In a production environment (like a Linux server), you should rely on the operating system's Cron scheduler. You only need to add a single entry to your server's crontab that pings Laravel every minute. Laravel handles the 15-minute timing internally.

Run `crontab -e` on your server and add the following line:

    * * * * * cd /path-to-your-project && php artisan schedule:run >> /dev/null 2>&1

---

## 🪝 Testing Webhooks Locally

This application includes a webhook receiver at `/api/kount360-webhook-receiver` that strictly verifies X-Event-Signatures using RSA-PSS padding.

To test this locally from Kount's servers, use a secure tunnel (like Cloudflare) to expose your local environment:

1. Start your Laravel server:

    php artisan serve

2. Start your Cloudflare tunnel (forcing HTTP to avoid SSL panics in PHP):

    cloudflared tunnel --url http://127.0.0.1:8000

3. Copy the resulting `.trycloudflare.com` URL, append your API route (`/api/kount360-webhook-receiver`), and configure it in the Kount dashboard. Monitor `storage/logs/kount-*.log` to see real-time verification results!
