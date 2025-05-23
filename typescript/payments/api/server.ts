/**
 * Usage Instructions:
 * 
 * 1. Install dependencies:
 *    npm install express axios axios-retry jsonwebtoken timers
 * 
 * 2. Set required environment variables:
 *    - KOUNT_API_KEY: Your API key for authentication.
 *    - KOUNT_PUBLIC_KEY: Your public key for webhook signature verification.
 * 
 * 3. Start the server:
 *    ts-node server.ts
 * 
 * 4. Test the endpoint:
 *    curl --request POST \
 *      --url http://127.0.0.1:8000/process-transaction \
 *      --header 'Content-Type: application/json' \
 *      --data '{ "order_id": "12345", "transactions": [{ "processor": "PayPal", "payment": { "type": "PYPL", "payment_token": "TOKEN123" }, "subtotal": "1000", "order_total": "1050", "currency": "USD" }] }'
 * 
 * 5. The API handles automatic JWT token refreshing and retries failed requests with exponential backoff.
 */

import express from 'express';
import type { Request, Response } from 'express';
import axios from 'axios';
import axiosRetry from 'axios-retry';
import jwt from 'jsonwebtoken';
import { setTimeout } from 'timers/promises';
import fs from 'fs';
import path from 'path';
import util from 'util';
import crypto from 'crypto';


const app = express();
app.use(express.json({
    verify: (req: any, res, buf) => {
      req.rawBody = buf.toString('utf8');
    }
  }));

const LOG_FILE = path.join(__dirname, 'kount.log');

function logError(message: string) {
  const logEntry = `${new Date().toISOString()} - ERROR: ${message}\n`;
  fs.appendFileSync(LOG_FILE, logEntry);
}


const CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED"];
const AVS_STATUSES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];

// Function to simulate credit card authorization
type AuthorizationPayload = {
    merchantOrderId: string;
    transactions: Array<{
        authorizationStatus: {
            authResult: string;
            verificationResponse: {
                cvvStatus: string;
                avsStatus: string;
            };
        };
    }>;
};

function simulateCreditCardAuthorization(merchantOrderId: string): AuthorizationPayload {
    const authResult = Math.random() < 0.9 ? "APPROVED" : "DECLINED";
    const cvvStatus = CVV_STATUSES[Math.floor(Math.random() * CVV_STATUSES.length)];
    const avsStatus = AVS_STATUSES[Math.floor(Math.random() * AVS_STATUSES.length)];

    return {
      merchantOrderId: merchantOrderId,
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
}

// Constants For API
const API_KEY = process.env.KOUNT_API_KEY;
const KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true";
const RETRY_INTERVAL = 10000; // 10 seconds
const REFRESH_BUFFER = 120; // 2 minutes before expiration

// Consts For Webhook
const WEBHOOK_URL = "https://api-sandbox.kount.com/commerce/v2/webhooks";
const publicKeyBase64 = process.env.KOUNT_PUBLIC_KEY;
if (!publicKeyBase64) {
  throw new Error("KOUNT_PUBLIC_KEY environment variable not set.");
}
const publicKey = crypto.createPublicKey({
  key: Buffer.from(publicKeyBase64, "base64"),
  format: "der",
  type: "spki",
});

const timestampGrace = 5 * 60 * 1000; // 5 minutes in milliseconds

if (!API_KEY) {
    throw new Error("API_KEY environment variable not set.");
}

// Apply axiosRetry globally
axiosRetry(axios, {
    retries: 3,
    retryDelay: axiosRetry.exponentialDelay,
    retryCondition: (error) => 
        [403, 408, 429, 500, 502, 503, 504].includes(error.response?.status || 0),
});

class TokenManager {
    private static instance: TokenManager;
    private accessToken: string | null = null;
    private expiresAt: number = 0;

    private constructor() {
        this.refreshTokenLoop();
    }

    public static getInstance(): TokenManager {
        if (!TokenManager.instance) {
            TokenManager.instance = new TokenManager();
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
          const response = await axios({
              url: `https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token`,
              method: "post",
              headers: {
                  authorization: `Basic ${API_KEY}`,
              },
              params: {
                  grant_type: "client_credentials",
                  scope: "k1_integration_api",
              },
          });
  
          this.accessToken = response.data.access_token;
          const decoded: any = this.accessToken ? jwt.decode(this.accessToken) : null;
          this.expiresAt = decoded?.exp ?? Date.now() / 1000 + 3600;
  
          console.log("Token obtained:", this.accessToken);
      } catch (error: any) {
          logError(`Failed to fetch token: ${error}`);
      }
   }

    private async refreshTokenLoop(): Promise<void> {
        while (true) {
            const waitTime = Math.max((this.expiresAt - Date.now() / 1000 - REFRESH_BUFFER) * 1000, RETRY_INTERVAL);
            await setTimeout(waitTime);
            try {
                await this.refreshToken();
            } catch (error) {
                logError(`Failed to fetch token: ${error}`);
            }
        }
    }
}

const tokenManager = TokenManager.getInstance();

app.post('/process-transaction', async (req, res) => {
    try {
      const payload = JSON.parse(JSON.stringify(req.body));
      console.log("Processing transaction:", JSON.stringify(payload, null, 2));
      const response = await processTransaction(payload);
      res.json(response);
    } catch (error) {
        logError(`Failed to process transaction: ${error}`);
        res.status(500).json({ error: "Failed to process transaction" });
    }
});

async function processTransaction(payload: any): Promise<any> {
    try {
        const token = await tokenManager.getAccessToken();
        const response = await axios.post(KOUNT_API_ENDPOINT, payload, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        const isPreAuth = payload.transactions.some(
            (transaction: any) => !transaction.authorizationStatus?.authResult
        );
        
        if (isPreAuth && response.data.order?.orderId) {
            setImmediate(() => patchTransaction(response.data.order.orderId, payload.order_id));
        }
        
        return response.data;
    } catch (error) {
        console.error("Error processing transaction", error);
        return { order: { riskInquiry: { decision: "APPROVE" } } }; // Default response after failure
    }
}

async function patchTransaction(kountOrderId: string, merchantOrderId: string): Promise<any> {
    try {
        const token = await tokenManager.getAccessToken();
        const url = `${KOUNT_API_ENDPOINT}/${kountOrderId}`;
        const simulatedAuthData = simulateCreditCardAuthorization(merchantOrderId);

        const response = await axios.patch(url, simulatedAuthData, {
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        return response.data;
    } catch (error) {
        logError(`Failed to patch transaction: ${error}`);
        return { order: { riskInquiry: { decision: "APPROVE" } } }; // Default response after failure
    }
}

// Express endpoint using the public key in verification
app.post("/kount360WebhookReceiver", (req: Request, res: Response): void => {
    const timestampHeader = req.headers["x-event-timestamp"] as string;
    const signatureBase64 = req.headers["x-event-signature"] as string;
    if (!timestampHeader || !signatureBase64) {
      res.status(400).send({ error: "Missing required headers" });
      return;
    }
  
    const timestamp = new Date(timestampHeader);
    const now = new Date();
    // Assume timestampGrace is defined elsewhere
    if (
      isNaN(timestamp.getTime()) ||
      now.getTime() - timestamp.getTime() > timestampGrace ||
      timestamp.getTime() - now.getTime() > timestampGrace
    ) {
      res.status(400).send("Invalid timestamp");
      return;
    }
    const rawBody = (req as any).rawBody;
    if (!rawBody) {
      res.status(400).send("Missing raw body");
      return;
    }

    // Verify the signature
    const verifier = crypto.createVerify("RSA-SHA256");
    verifier.update(Buffer.from(timestampHeader, 'utf8'));
    verifier.update(Buffer.from(rawBody, 'utf8'));
    verifier.end();
    
    const signature = Buffer.from(signatureBase64, "base64");
  
    const isVerified = verifier.verify(
      {
        key: publicKey,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        // Optionally, if needed:
        saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
      },
      signature
    );
  
    if (!isVerified) {
      logError("Signature verification failed");
      console.log("Signature verification failed:", signature.toString("base64"));
      res.status(403).send("Could not verify signature");
      return;
    }
  
    // Process the valid webhook payload
    logError("Webhook received and verified successfully");
    console.log("Webhook payload:", JSON.stringify(req.body, null, 2));
    res.sendStatus(200);
  });

app.listen(8000, () => {
    logError("Server running on port 8000");
});

export { processTransaction, patchTransaction, simulateCreditCardAuthorization };
