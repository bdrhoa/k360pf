# Kount JWT authentication

This local package provides the shared `TokenManager` used by the Kount
TypeScript examples. It obtains a client-credentials access token, caches it,
and refreshes it two minutes before expiration.

## Build

```bash
cd typescript/jwt_auth
npm ci
npm run build
```

The compiled `dist` files are checked in because sibling examples consume this
package through a local npm `file:` dependency.

## Use from an example

Add the package to the example's dependencies:

```json
"@kount/k360-jwt-auth": "file:../jwt_auth"
```

Then create or retrieve the process-wide manager:

```typescript
import { TokenManager } from "@kount/k360-jwt-auth";

const tokenManager = TokenManager.getInstance({
  apiKey: process.env.KOUNT_API_KEY ?? "",
});

const accessToken = await tokenManager.getAccessToken();
```
