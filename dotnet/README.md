# Kount 360 .NET Example

This folder contains a .NET 8 solution that demonstrates Kount 360 authentication, New Account Opening (NAO), Account Protection Login Pro, Payment Fraud order evaluation, and webhook signature verification.

## Projects

- `KountJwtAuth`: shared library for JWT token management and webhook signature verification.
- `ClientDemoApp`: console app that gets a Kount access token, submits demo NAO V2 and Login V2 inquiries, and evaluates a demo Payment Fraud order.
- `KountWebhook`: ASP.NET Core webhook receiver that verifies Kount webhook signatures.
- `KountJwtAuth.Tests` and `KountWebhook.Tests`: unit tests for the shared library and webhook receiver.

## Prerequisites

- .NET SDK 8.0.408 or compatible .NET 8 SDK.
- Kount API credentials for running `ClientDemoApp`.
- Kount webhook public key for running webhook signature verification.

## Configuration

Set these environment variables before running `ClientDemoApp`:

```bash
export KOUNT_API_KEY="your-basic-auth-api-key"
export KOUNT_API_BASE_URL="https://api-sandbox.kount.com"
```

Optional Client Demo variables:

```bash
export KOUNT_CHANNEL="DEFAULT"
export KOUNT_CLIENT_ID="your-client-id"
```

`KOUNT_CHANNEL` also sets the channel on the Login V2 inquiry and Payment Fraud order. It defaults to `DEFAULT`.
`KOUNT_CLIENT_ID` is used only by the NAO example to add shared context.

Set this environment variable before running webhook signature verification:

```bash
export KOUNT_PUBLIC_KEY="base64-encoded-public-key"
```

## Run the Client Demo

From this `dotnet` folder:

```bash
dotnet run --project ClientDemoApp/ClientDemoApp.csproj
```

`ClientDemoApp` writes its output to a rolling Serilog file named `kount.log` in the directory where the app is run. The app does not print API responses to the terminal, so check the log file to see the token refresh, NAO request and response, Login request and response, Payment Fraud request and response, and any retry-related failures.

```bash
tail -f kount.log
```

After the NAO call, the app submits the Account Protection inquiry with [`POST /login/v2`](https://api.kount.com/login/help#operation/LoginService_LoginV2), then evaluates the order with `POST /commerce/v2/orders?riskInquiry=true`. It then keeps running so token auto-refresh can continue. Stop it with `Ctrl+C`.

## How Polly Is Used

`ClientDemoApp` uses Polly through `Microsoft.Extensions.Http.Polly` and typed `HttpClient` registration in `Program.cs`.

`TokenService`, `NewAccountOpeningClient`, `LoginV2Client`, and `PaymentFraudClient` are registered with `AddHttpClient(...).AddPolicyHandler(GetRetryPolicy())`. That means the retry behavior is applied by dependency injection when each typed client receives its `HttpClient`.

The API clients do not create or call Polly directly. They build and send their requests, while `Program.cs` owns cross-cutting HTTP behavior such as retries.

The retry policy handles transient HTTP errors using Polly's `HttpPolicyExtensions.HandleTransientHttpError()`, then retries three times with exponential backoff and jitter:

```csharp
private static IAsyncPolicy<HttpResponseMessage> GetRetryPolicy()
{
    return HttpPolicyExtensions
        .HandleTransientHttpError()
        .WaitAndRetryAsync(3, retryAttempt =>
        {
            var exponentialDelay = TimeSpan.FromSeconds(Math.Pow(2, retryAttempt));
            var jitteredDelay = TimeSpan.FromMilliseconds(
                Random.Shared.NextDouble() * exponentialDelay.TotalMilliseconds);

            return jitteredDelay;
        });
}
```

This produces a randomized delay between zero and the current exponential delay for each retry attempt. The jitter helps avoid many clients retrying at the same exact time.

## Run the Webhook Example

From this `dotnet` folder:

```bash
dotnet run --project KountWebhook/KountWebhook.csproj
```

In development, Swagger is enabled by the ASP.NET Core pipeline. The webhook endpoint is:

```text
POST /Kount360WebhookReceiver
```

Requests must include:

- `X-Event-Timestamp`
- `X-Event-Signature`
- A JSON request body

## Build and Test

Build the solution:

```bash
dotnet build Kount.sln
```

Run tests:

```bash
dotnet test Kount.sln
```

To generate an HTML test report:

```bash
./rt.sh
```
