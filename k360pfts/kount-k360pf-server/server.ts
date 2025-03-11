/**
 * Usage Instructions:
 * 
 * 1. Install dependencies:
 *    npm install express axios axios-retry jsonwebtoken timers
 * 
 * 2. Set required environment variables:
 *    - API_KEY: Your API key for authentication.
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

const app = express();
app.use(express.json());

const LOG_FILE = path.join(__dirname, 'kount.log');

function logError(message: string) {
  const logEntry = `${new Date().toISOString()} - ERROR: ${message}\n`;
  fs.appendFileSync(LOG_FILE, logEntry);
}


const CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED"];
const AVS_STATUSES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];

// Function to simulate credit card authorization
type AuthorizationPayload = {
    order_id: string;
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
}

// Constants
const API_KEY = process.env.API_KEY;
const AUTH_SERVER_URL = "https://login.kount.com/oauth2/token";
const KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true";
const RETRY_INTERVAL = 10000; // 10 seconds
const REFRESH_BUFFER = 120; // 2 minutes before expiration

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
            const response = await axios.post(AUTH_SERVER_URL, {
                grant_type: "client_credentials",
                scope: "k1_integration_api",
            }, {
                headers: {
                    Authorization: `Basic ${API_KEY}`,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout: 10000,
            });
            this.accessToken = response.data.access_token;
            const decoded: any = this.accessToken ? jwt.decode(this.accessToken) : null;
            this.expiresAt = decoded?.exp ?? Date.now() / 1000 + 3600;
        } catch (error) {
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
        const payload = req.body;
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

app.listen(8000, () => {
    logError("Server running on port 8000");
});

export { processTransaction, patchTransaction, simulateCreditCardAuthorization };
