"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = require("express");
var axios_1 = require("axios");
var jsonwebtoken_1 = require("jsonwebtoken");
var p_retry_1 = require("p-retry");
var dotenv_1 = require("dotenv");
dotenv_1.default.config();
var app = (0, express_1.default)();
app.use(express_1.default.json());
var PORT = 8000;
// Constants
var REFRESH_TIME_BUFFER = 2 * 60 * 1000; // Refresh 2 minutes before expiry
var AUTH_SERVER_URL = 'https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token';
var KOUNT_API_ENDPOINT = 'https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true';
// API Key (Should be in environment variables)
var API_KEY = process.env.API_KEY || 'YOUR_API_KEY_HERE';
if (!API_KEY) {
    throw new Error('API_KEY is not set in environment variables.');
}
// Possible CVV and AVS statuses
var CVV_STATUSES = ['MATCH', 'NO_MATCH', 'NOT_PROVIDED'];
var AVS_STATUSES = ['A', 'N', 'X', 'Y', 'Z'];
// Token Manager Singleton
var TokenManager = /** @class */ (function () {
    function TokenManager() {
        this.accessToken = null;
    }
    TokenManager.getInstance = function () {
        if (!TokenManager.instance) {
            TokenManager.instance = new TokenManager();
        }
        return TokenManager.instance;
    };
    TokenManager.prototype.getAccessToken = function () {
        return this.accessToken;
    };
    TokenManager.prototype.setAccessToken = function (token) {
        this.accessToken = token;
    };
    return TokenManager;
}());
var tokenManager = TokenManager.getInstance();
/**
 * Fetch or refresh the JWT token with retries.
 */
var fetchOrRefreshToken = function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        return [2 /*return*/, (0, p_retry_1.default)(function () { return __awaiter(void 0, void 0, void 0, function () {
                var response, token, error_1;
                return __generator(this, function (_a) {
                    switch (_a.label) {
                        case 0:
                            _a.trys.push([0, 2, , 3]);
                            return [4 /*yield*/, axios_1.default.post(AUTH_SERVER_URL, new URLSearchParams({ grant_type: 'client_credentials', scope: 'k1_integration_api' }), {
                                    headers: {
                                        Authorization: "Basic ".concat(API_KEY),
                                        'Content-Type': 'application/x-www-form-urlencoded',
                                    },
                                    timeout: 10000,
                                })];
                        case 1:
                            response = _a.sent();
                            token = response.data.access_token;
                            tokenManager.setAccessToken(token);
                            console.log('Token obtained:', token);
                            return [2 /*return*/, token];
                        case 2:
                            error_1 = _a.sent();
                            console.error('Failed to fetch token:', error_1);
                            throw new Error('Failed to fetch token');
                        case 3: return [2 /*return*/];
                    }
                });
            }); }, { retries: 3, minTimeout: 10000 })];
    });
}); };
/**
 * Start a background process to refresh the token before expiration.
 */
var startTokenRefreshTimer = function () { return __awaiter(void 0, void 0, void 0, function () {
    var _loop_1;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                _loop_1 = function () {
                    var currentToken, timeUntilRefresh, decoded, expTime;
                    return __generator(this, function (_b) {
                        switch (_b.label) {
                            case 0:
                                currentToken = tokenManager.getAccessToken();
                                timeUntilRefresh = 0;
                                if (currentToken) {
                                    try {
                                        decoded = jsonwebtoken_1.default.decode(currentToken);
                                        expTime = ((decoded === null || decoded === void 0 ? void 0 : decoded.exp) * 1000) - REFRESH_TIME_BUFFER;
                                        timeUntilRefresh = expTime - Date.now();
                                    }
                                    catch (error) {
                                        console.error('Error decoding JWT:', error);
                                    }
                                }
                                return [4 /*yield*/, new Promise(function (resolve) { return setTimeout(resolve, Math.max(timeUntilRefresh, 0)); })];
                            case 1:
                                _b.sent();
                                return [4 /*yield*/, fetchOrRefreshToken()];
                            case 2:
                                _b.sent();
                                return [2 /*return*/];
                        }
                    });
                };
                _a.label = 1;
            case 1:
                if (!true) return [3 /*break*/, 3];
                return [5 /*yield**/, _loop_1()];
            case 2:
                _a.sent();
                return [3 /*break*/, 1];
            case 3: return [2 /*return*/];
        }
    });
}); };
// Start token refresh task
fetchOrRefreshToken();
startTokenRefreshTimer();
/**
 * Function to call the Kount API with retries for HTTP 408 errors.
 */
var makeKountApiRequest = function (payload) { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        return [2 /*return*/, (0, p_retry_1.default)(function () { return __awaiter(void 0, void 0, void 0, function () {
                var response, error_2;
                var _a;
                return __generator(this, function (_b) {
                    switch (_b.label) {
                        case 0:
                            _b.trys.push([0, 2, , 3]);
                            return [4 /*yield*/, axios_1.default.post(KOUNT_API_ENDPOINT, payload, {
                                    headers: {
                                        Authorization: "Bearer ".concat(tokenManager.getAccessToken()),
                                        'Content-Type': 'application/json',
                                    },
                                })];
                        case 1:
                            response = _b.sent();
                            return [2 /*return*/, response.data];
                        case 2:
                            error_2 = _b.sent();
                            if (((_a = error_2.response) === null || _a === void 0 ? void 0 : _a.status) === 408) {
                                console.warn('Retrying Kount API due to timeout (408)...');
                                throw error_2;
                            }
                            else {
                                console.error('Kount API error:', error_2);
                                throw new Error('Failed to call Kount API');
                            }
                            return [3 /*break*/, 3];
                        case 3: return [2 /*return*/];
                    }
                });
            }); }, { retries: 3, factor: 2, minTimeout: 1000, maxTimeout: 10000 })];
    });
}); };
/**
 * Simulate a credit card authorization decision.
 */
var simulateCreditCardAuthorization = function (merchantOrderId) {
    var authResult = Math.random() < 0.8 ? 'APPROVED' : 'DECLINED';
    var cvvStatus = CVV_STATUSES[Math.floor(Math.random() * CVV_STATUSES.length)];
    var avsStatus = AVS_STATUSES[Math.floor(Math.random() * AVS_STATUSES.length)];
    return {
        order_id: merchantOrderId,
        transactions: [
            {
                authorizationStatus: {
                    authResult: authResult,
                    verificationResponse: {
                        cvvStatus: cvvStatus,
                        avsStatus: avsStatus,
                    },
                },
            },
        ],
    };
};
/**
 * Patch the credit card authorization at Kount API.
 */
var patchCreditCardAuthorization = function (kountOrderId, merchantOrderId) { return __awaiter(void 0, void 0, void 0, function () {
    var url, authorizationPayload, error_3;
    return __generator(this, function (_a) {
        switch (_a.label) {
            case 0:
                url = "https://api-sandbox.kount.com/commerce/v2/orders/".concat(kountOrderId);
                authorizationPayload = simulateCreditCardAuthorization(merchantOrderId);
                _a.label = 1;
            case 1:
                _a.trys.push([1, 3, , 4]);
                return [4 /*yield*/, axios_1.default.patch(url, authorizationPayload, {
                        headers: {
                            Authorization: "Bearer ".concat(tokenManager.getAccessToken()),
                            'Content-Type': 'application/json',
                        },
                    })];
            case 2:
                _a.sent();
                console.log("Successfully patched authorization for order: ".concat(kountOrderId));
                return [3 /*break*/, 4];
            case 3:
                error_3 = _a.sent();
                console.error('Failed to patch authorization:', error_3);
                return [3 /*break*/, 4];
            case 4: return [2 /*return*/];
        }
    });
}); };
/**
 * Process transaction and call the Kount API.
 */
app.post('/process-transaction', function (req, res) { return __awaiter(void 0, void 0, void 0, function () {
    var incomingData, payload, response, decision, kountOrderId_1, merchantOrderId_1, transaction, isPreAuth, error_4;
    var _a, _b, _c, _d, _e;
    return __generator(this, function (_f) {
        switch (_f.label) {
            case 0:
                _f.trys.push([0, 2, , 3]);
                incomingData = req.body;
                payload = incomingData;
                return [4 /*yield*/, makeKountApiRequest(payload)];
            case 1:
                response = _f.sent();
                decision = ((_b = (_a = response === null || response === void 0 ? void 0 : response.order) === null || _a === void 0 ? void 0 : _a.riskInquiry) === null || _b === void 0 ? void 0 : _b.decision) || 'UNKNOWN';
                kountOrderId_1 = ((_c = response === null || response === void 0 ? void 0 : response.order) === null || _c === void 0 ? void 0 : _c.orderId) || 'UNKNOWN';
                merchantOrderId_1 = (incomingData === null || incomingData === void 0 ? void 0 : incomingData.order_id) || 'UNKNOWN';
                transaction = (_d = incomingData === null || incomingData === void 0 ? void 0 : incomingData.transactions) === null || _d === void 0 ? void 0 : _d[0];
                isPreAuth = !((_e = transaction === null || transaction === void 0 ? void 0 : transaction.authorizationStatus) === null || _e === void 0 ? void 0 : _e.authResult);
                // Schedule the authorization patching only if necessary
                if (isPreAuth &&
                    kountOrderId_1 !== 'UNKNOWN' &&
                    merchantOrderId_1 !== 'UNKNOWN' &&
                    decision === 'APPROVE') {
                    setTimeout(function () { return patchCreditCardAuthorization(kountOrderId_1, merchantOrderId_1); }, 0);
                }
                return [2 /*return*/, res.json(response)];
            case 2:
                error_4 = _f.sent();
                console.error('Error processing transaction:', error_4);
                return [2 /*return*/, res.status(500).json({ error: 'Transaction processing failed' })];
            case 3: return [2 /*return*/];
        }
    });
}); });
// Start the Express server
app.listen(PORT, function () {
    console.log("Server running on http://127.0.0.1:".concat(PORT));
});
