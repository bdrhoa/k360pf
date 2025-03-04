import express, { Request, Response } from 'express';
import axios, { AxiosResponse } from 'axios';
import jwt from 'jsonwebtoken';
import pRetry from 'p-retry';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(express.json());

const PORT = 8000;

// Constants
const REFRESH_TIME_BUFFER = 2 * 60 * 1000; // Refresh 2 minutes before expiry
const AUTH_SERVER_URL = 'https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token';
const KOUNT_API_ENDPOINT = 'https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true';

// API Key (Should be in environment variables)
const API_KEY = process.env.API_KEY || 'YOUR_API_KEY_HERE';
if (!API_KEY) {
  throw new Error('API_KEY is not set in environment variables.');
}

// Possible CVV and AVS statuses
const CVV_STATUSES = ['MATCH', 'NO_MATCH', 'NOT_PROVIDED'];
const AVS_STATUSES = ['A', 'N', 'X', 'Y', 'Z'];

// Token Manager Singleton
class TokenManager {
  private static instance: TokenManager;
  private accessToken: string | null = null;

  private constructor() {}

  public static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  setAccessToken(token: string): void {
    this.accessToken = token;
  }
}

const tokenManager = TokenManager.getInstance();

/**
 * Fetch or refresh the JWT token with retries.
 */
const fetchOrRefreshToken = async (): Promise<string> => {
  return pRetry(async () => {
    try {
      const response: AxiosResponse<any> = await axios.post(
        AUTH_SERVER_URL,
        new URLSearchParams({ grant_type: 'client_credentials', scope: 'k1_integration_api' }),
        {
          headers: {
            Authorization: `Basic ${API_KEY}`,
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          timeout: 10_000,
        }
      );

      const token = response.data.access_token;
      tokenManager.setAccessToken(token);
      console.log('Token obtained:', token);
      return token;
    } catch (error) {
      console.error('Failed to fetch token:', error);
      throw new Error('Failed to fetch token');
    }
  }, { retries: 3, minTimeout: 10_000 });
};

/**
 * Start a background process to refresh the token before expiration.
 */
const startTokenRefreshTimer = async () => {
  while (true) {
    const currentToken = tokenManager.getAccessToken();
    let timeUntilRefresh = 0;

    if (currentToken) {
      try {
        const decoded: any = jwt.decode(currentToken);
        const expTime = (decoded?.exp * 1000) - REFRESH_TIME_BUFFER;
        timeUntilRefresh = expTime - Date.now();
      } catch (error) {
        console.error('Error decoding JWT:', error);
      }
    }

    await new Promise(resolve => setTimeout(resolve, Math.max(timeUntilRefresh, 0)));
    await fetchOrRefreshToken();
  }
};

// Start token refresh task
fetchOrRefreshToken();
startTokenRefreshTimer();

/**
 * Function to call the Kount API with retries for HTTP 408 errors.
 */
const makeKountApiRequest = async (payload: any): Promise<any> => {
  return pRetry(async () => {
    try {
      const response: AxiosResponse<any> = await axios.post(KOUNT_API_ENDPOINT, payload, {
        headers: {
          Authorization: `Bearer ${tokenManager.getAccessToken()}`,
          'Content-Type': 'application/json',
        },
      });

      return response.data;
    } catch (error: any) {
      if (error.response?.status === 408) {
        console.warn('Retrying Kount API due to timeout (408)...');
        throw error;
      } else {
        console.error('Kount API error:', error);
        throw new Error('Failed to call Kount API');
      }
    }
  }, { retries: 3, factor: 2, minTimeout: 1000, maxTimeout: 10_000 });
};

/**
 * Simulate a credit card authorization decision.
 */
const simulateCreditCardAuthorization = (merchantOrderId: string) => {
  const authResult = Math.random() < 0.8 ? 'APPROVED' : 'DECLINED';
  const cvvStatus = CVV_STATUSES[Math.floor(Math.random() * CVV_STATUSES.length)];
  const avsStatus = AVS_STATUSES[Math.floor(Math.random() * AVS_STATUSES.length)];

  return {
    order_id: merchantOrderId,
    transactions: [
      {
        authorizationStatus: {
          authResult,
          verificationResponse: {
            cvvStatus,
            avsStatus,
          },
        },
      },
    ],
  };
};

/**
 * Patch the credit card authorization at Kount API.
 */
const patchCreditCardAuthorization = async (kountOrderId: string, merchantOrderId: string) => {
  const url = `https://api-sandbox.kount.com/commerce/v2/orders/${kountOrderId}`;
  const authorizationPayload = simulateCreditCardAuthorization(merchantOrderId);

  try {
    await axios.patch(url, authorizationPayload, {
      headers: {
        Authorization: `Bearer ${tokenManager.getAccessToken()}`,
        'Content-Type': 'application/json',
      },
    });

    console.log(`Successfully patched authorization for order: ${kountOrderId}`);
  } catch (error) {
    console.error('Failed to patch authorization:', error);
  }
};

/**
 * Process transaction and call the Kount API.
 */
app.post('/process-transaction', async (req: Request, res: Response) => {
  try {
    const incomingData = req.body;
    const payload = incomingData; // Directly using input data for now
    const response = await makeKountApiRequest(payload);

    const decision = response?.order?.riskInquiry?.decision || 'UNKNOWN';
    const kountOrderId = response?.order?.orderId || 'UNKNOWN';
    const merchantOrderId = incomingData?.order_id || 'UNKNOWN';

    // Check if authorizationStatus exists
    const transaction = incomingData?.transactions?.[0];
    const isPreAuth = !transaction?.authorizationStatus?.authResult;

    // Schedule the authorization patching only if necessary
    if (
      isPreAuth &&
      kountOrderId !== 'UNKNOWN' &&
      merchantOrderId !== 'UNKNOWN' &&
      decision === 'APPROVE'
    ) {
      setTimeout(() => patchCreditCardAuthorization(kountOrderId, merchantOrderId), 0);
    }

    return res.json(response);
  } catch (error) {
    console.error('Error processing transaction:', error);
    return res.status(500).json({ error: 'Transaction processing failed' });
  }
});

// Start the Express server
app.listen(PORT, () => {
  console.log(`Server running on http://127.0.0.1:${PORT}`);
});