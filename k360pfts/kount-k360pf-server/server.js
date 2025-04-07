"use strict";
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
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.processTransaction = processTransaction;
exports.patchTransaction = patchTransaction;
exports.simulateCreditCardAuthorization = simulateCreditCardAuthorization;
const express_1 = __importDefault(require("express"));
const axios_1 = __importDefault(require("axios"));
const axios_retry_1 = __importDefault(require("axios-retry"));
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const promises_1 = require("timers/promises");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const crypto_1 = __importDefault(require("crypto"));
const app = (0, express_1.default)();
app.use(express_1.default.json());
const LOG_FILE = path_1.default.join(__dirname, 'kount.log');
function logError(message) {
    const logEntry = `${new Date().toISOString()} - ERROR: ${message}\n`;
    fs_1.default.appendFileSync(LOG_FILE, logEntry);
}
const CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED"];
const AVS_STATUSES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];
function simulateCreditCardAuthorization(merchantOrderId) {
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
const AUTH_SERVER_URL = "https://login.kount.com/oauth2/token";
const KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true";
const RETRY_INTERVAL = 10000; // 10 seconds
const REFRESH_BUFFER = 120; // 2 minutes before expiration
// Consts For Webhook
const WEBHOOK_URL = "https://api-sandbox.kount.com/commerce/v2/webhooks";
const publicKeyBase64 = process.env.KOUNT_PUBLIC_KEY;
if (!publicKeyBase64) {
    throw new Error("KOUNT_PUBLIC_KEY environment variable not set.");
}
const publicKey = crypto_1.default.createPublicKey({
    key: Buffer.from(publicKeyBase64, "base64"),
    format: "der",
    type: "spki",
});
//publicKey.padding = crypto.constants.RSA_PKCS1_PSS_PADDING;
const timestampGrace = 5 * 60 * 1000; // 5 minutes in milliseconds
if (!API_KEY) {
    throw new Error("API_KEY environment variable not set.");
}
console.log("API_KEY:", API_KEY);
// Apply axiosRetry globally
(0, axios_retry_1.default)(axios_1.default, {
    retries: 3,
    retryDelay: axios_retry_1.default.exponentialDelay,
    retryCondition: (error) => { var _a; return [403, 408, 429, 500, 502, 503, 504].includes(((_a = error.response) === null || _a === void 0 ? void 0 : _a.status) || 0); },
});
class TokenManager {
    constructor() {
        this.accessToken = null;
        this.expiresAt = 0;
        this.refreshTokenLoop();
    }
    static getInstance() {
        if (!TokenManager.instance) {
            TokenManager.instance = new TokenManager();
        }
        return TokenManager.instance;
    }
    getAccessToken() {
        return __awaiter(this, void 0, void 0, function* () {
            if (!this.accessToken || Date.now() / 1000 >= this.expiresAt - REFRESH_BUFFER) {
                yield this.refreshToken();
            }
            return this.accessToken;
        });
    }
    refreshToken() {
        return __awaiter(this, void 0, void 0, function* () {
            var _a;
            try {
                const response = yield (0, axios_1.default)({
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
                const decoded = this.accessToken ? jsonwebtoken_1.default.decode(this.accessToken) : null;
                this.expiresAt = (_a = decoded === null || decoded === void 0 ? void 0 : decoded.exp) !== null && _a !== void 0 ? _a : Date.now() / 1000 + 3600;
                console.log("Token obtained:", this.accessToken);
            }
            catch (error) {
                logError(`Failed to fetch token: ${error}`);
            }
        });
    }
    refreshTokenLoop() {
        return __awaiter(this, void 0, void 0, function* () {
            while (true) {
                const waitTime = Math.max((this.expiresAt - Date.now() / 1000 - REFRESH_BUFFER) * 1000, RETRY_INTERVAL);
                yield (0, promises_1.setTimeout)(waitTime);
                try {
                    yield this.refreshToken();
                }
                catch (error) {
                    logError(`Failed to fetch token: ${error}`);
                }
            }
        });
    }
}
const tokenManager = TokenManager.getInstance();
app.post('/process-transaction', (req, res) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        const payload = JSON.parse(JSON.stringify(req.body));
        console.log("Processing transaction:", JSON.stringify(payload, null, 2));
        const response = yield processTransaction(payload);
        res.json(response);
    }
    catch (error) {
        logError(`Failed to process transaction: ${error}`);
        res.status(500).json({ error: "Failed to process transaction" });
    }
}));
function processTransaction(payload) {
    return __awaiter(this, void 0, void 0, function* () {
        var _a;
        try {
            const token = yield tokenManager.getAccessToken();
            const response = yield axios_1.default.post(KOUNT_API_ENDPOINT, payload, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            const isPreAuth = payload.transactions.some((transaction) => { var _a; return !((_a = transaction.authorizationStatus) === null || _a === void 0 ? void 0 : _a.authResult); });
            if (isPreAuth && ((_a = response.data.order) === null || _a === void 0 ? void 0 : _a.orderId)) {
                setImmediate(() => patchTransaction(response.data.order.orderId, payload.order_id));
            }
            return response.data;
        }
        catch (error) {
            console.error("Error processing transaction", error);
            return { order: { riskInquiry: { decision: "APPROVE" } } }; // Default response after failure
        }
    });
}
function patchTransaction(kountOrderId, merchantOrderId) {
    return __awaiter(this, void 0, void 0, function* () {
        try {
            const token = yield tokenManager.getAccessToken();
            const url = `${KOUNT_API_ENDPOINT}/${kountOrderId}`;
            const simulatedAuthData = simulateCreditCardAuthorization(merchantOrderId);
            const response = yield axios_1.default.patch(url, simulatedAuthData, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            return response.data;
        }
        catch (error) {
            logError(`Failed to patch transaction: ${error}`);
            return { order: { riskInquiry: { decision: "APPROVE" } } }; // Default response after failure
        }
    });
}
// Express endpoint using the public key in verification
app.post("/kount360WebhookReceiver", (req, res) => {
    const timestampHeader = req.headers["x-event-timestamp"];
    const signatureBase64 = req.headers["x-event-signature"];
    if (!timestampHeader || !signatureBase64) {
        res.status(400).send({ error: "Missing required headers" });
        return;
    }
    const timestamp = new Date(timestampHeader);
    const now = new Date();
    // Assume timestampGrace is defined elsewhere
    if (isNaN(timestamp.getTime()) ||
        now.getTime() - timestamp.getTime() > timestampGrace ||
        timestamp.getTime() - now.getTime() > timestampGrace) {
        res.status(400).send("Invalid timestamp");
        return;
    }
    const verifier = crypto_1.default.createVerify("RSA-SHA256");
    console.log("Timestamp Header:", timestampHeader);
    console.log(JSON.stringify(req.body));
    console.log("Signature Base64:", signatureBase64);
    verifier.update(timestampHeader);
    verifier.update(JSON.stringify(req.body));
    const signature = Buffer.from(signatureBase64, "base64");
    const isVerified = verifier.verify({
        key: publicKey,
        padding: crypto_1.default.constants.RSA_PKCS1_PSS_PADDING,
        // Optionally, if needed:
        // saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
    }, signature);
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
