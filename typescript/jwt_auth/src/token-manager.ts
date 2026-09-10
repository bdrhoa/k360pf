import https from "https";
import { setTimeout } from "timers/promises";

const AUTH_SERVER_URL = "https://login-uat.equifax.com/as/token";
const AUTH_SCOPE = "k1_integration_api";
const RETRY_INTERVAL = 10_000;
const REFRESH_BUFFER = 120;

export type TokenManagerOptions = {
  apiKey: string;
  logError?: (message: string) => void;
};

type TokenResponse = {
  access_token?: string;
};

function decodeExpiration(accessToken: string): number | undefined {
  const encodedPayload = accessToken.split(".")[1];
  if (!encodedPayload) {
    return undefined;
  }

  try {
    const payload = JSON.parse(
      Buffer.from(encodedPayload, "base64url").toString("utf8"),
    ) as { exp?: unknown };
    return typeof payload.exp === "number" ? payload.exp : undefined;
  } catch {
    return undefined;
  }
}

/**
 * Obtains and refreshes the JWT used to authenticate with Kount APIs.
 *
 * Create one instance and share it across the application features that need
 * Kount API access.
 */
export class TokenManager {
  private static instance: TokenManager;
  private accessToken: string | null = null;
  private expiresAt = 0;
  private readonly apiKey: string;
  private readonly logError: (message: string) => void;

  private constructor({ apiKey, logError = console.error }: TokenManagerOptions) {
    if (!apiKey) {
      throw new Error("KOUNT_API_KEY environment variable not set.");
    }

    this.apiKey = apiKey;
    this.logError = logError;
    void this.refreshTokenLoop();
  }

  public static getInstance(options: TokenManagerOptions): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager(options);
    }

    return TokenManager.instance;
  }

  public async getAccessToken(): Promise<string> {
    if (!this.accessToken || Date.now() / 1000 >= this.expiresAt - REFRESH_BUFFER) {
      await this.refreshToken();
    }

    return this.accessToken as string;
  }

  private async refreshToken(): Promise<void> {
    try {
      this.accessToken = await this.requestAccessToken();
      this.expiresAt =
        decodeExpiration(this.accessToken) ?? Date.now() / 1000 + 3600;

      console.log("Kount access token obtained.");
    } catch (error) {
      this.logError(`Failed to fetch token: ${error}`);
      throw error;
    }
  }

  private requestAccessToken(): Promise<string> {
    const url = new URL(AUTH_SERVER_URL);
    const requestBody = new URLSearchParams({
      grant_type: "client_credentials",
      scope: AUTH_SCOPE,
    }).toString();

    return new Promise((resolve, reject) => {
      const request = https.request(
        url,
        {
          method: "POST",
          headers: {
            authorization: `Basic ${this.apiKey}`,
            "content-length": Buffer.byteLength(requestBody),
            "content-type": "application/x-www-form-urlencoded",
          },
        },
        (response) => {
          let responseBody = "";
          response.setEncoding("utf8");
          response.on("data", (chunk: string) => {
            responseBody += chunk;
          });
          response.on("end", () => {
            if (!response.statusCode || response.statusCode >= 400) {
              reject(
                new Error(`Token endpoint returned HTTP ${response.statusCode ?? "unknown"}.`),
              );
              return;
            }

            try {
              const tokenResponse = JSON.parse(responseBody) as TokenResponse;
              if (!tokenResponse.access_token) {
                reject(new Error("Token endpoint response did not contain an access token."));
                return;
              }
              resolve(tokenResponse.access_token);
            } catch (error) {
              reject(error);
            }
          });
        },
      );

      request.on("error", reject);
      request.write(requestBody);
      request.end();
    });
  }

  private async refreshTokenLoop(): Promise<void> {
    while (true) {
      const waitTime = Math.max(
        (this.expiresAt - Date.now() / 1000 - REFRESH_BUFFER) * 1000,
        RETRY_INTERVAL,
      );
      await setTimeout(waitTime);
      try {
        await this.refreshToken();
      } catch {
        // refreshToken logs the failure; the loop retries after RETRY_INTERVAL.
      }
    }
  }
}
