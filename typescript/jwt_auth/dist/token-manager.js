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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.TokenManager = void 0;
const https_1 = __importDefault(require("https"));
const promises_1 = require("timers/promises");
const AUTH_SERVER_URL = "https://login-uat.equifax.com/as/token";
const AUTH_SCOPE = "k1_integration_api";
const RETRY_INTERVAL = 10000;
const REFRESH_BUFFER = 120;
function decodeExpiration(accessToken) {
    const encodedPayload = accessToken.split(".")[1];
    if (!encodedPayload) {
        return undefined;
    }
    try {
        const payload = JSON.parse(Buffer.from(encodedPayload, "base64url").toString("utf8"));
        return typeof payload.exp === "number" ? payload.exp : undefined;
    }
    catch (_a) {
        return undefined;
    }
}
/**
 * Obtains and refreshes the JWT used to authenticate with Kount APIs.
 *
 * Create one instance and share it across the application features that need
 * Kount API access.
 */
class TokenManager {
    constructor({ apiKey, logError = console.error }) {
        this.accessToken = null;
        this.expiresAt = 0;
        if (!apiKey) {
            throw new Error("KOUNT_API_KEY environment variable not set.");
        }
        this.apiKey = apiKey;
        this.logError = logError;
        void this.refreshTokenLoop();
    }
    static getInstance(options) {
        if (!TokenManager.instance) {
            TokenManager.instance = new TokenManager(options);
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
                this.accessToken = yield this.requestAccessToken();
                this.expiresAt =
                    (_a = decodeExpiration(this.accessToken)) !== null && _a !== void 0 ? _a : Date.now() / 1000 + 3600;
                console.log("Kount access token obtained.");
            }
            catch (error) {
                this.logError(`Failed to fetch token: ${error}`);
                throw error;
            }
        });
    }
    requestAccessToken() {
        const url = new URL(AUTH_SERVER_URL);
        const requestBody = new URLSearchParams({
            grant_type: "client_credentials",
            scope: AUTH_SCOPE,
        }).toString();
        return new Promise((resolve, reject) => {
            const request = https_1.default.request(url, {
                method: "POST",
                headers: {
                    authorization: `Basic ${this.apiKey}`,
                    "content-length": Buffer.byteLength(requestBody),
                    "content-type": "application/x-www-form-urlencoded",
                },
            }, (response) => {
                let responseBody = "";
                response.setEncoding("utf8");
                response.on("data", (chunk) => {
                    responseBody += chunk;
                });
                response.on("end", () => {
                    var _a;
                    if (!response.statusCode || response.statusCode >= 400) {
                        reject(new Error(`Token endpoint returned HTTP ${(_a = response.statusCode) !== null && _a !== void 0 ? _a : "unknown"}.`));
                        return;
                    }
                    try {
                        const tokenResponse = JSON.parse(responseBody);
                        if (!tokenResponse.access_token) {
                            reject(new Error("Token endpoint response did not contain an access token."));
                            return;
                        }
                        resolve(tokenResponse.access_token);
                    }
                    catch (error) {
                        reject(error);
                    }
                });
            });
            request.on("error", reject);
            request.write(requestBody);
            request.end();
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
                catch (_a) {
                    // refreshToken logs the failure; the loop retries after RETRY_INTERVAL.
                }
            }
        });
    }
}
exports.TokenManager = TokenManager;
