export type TokenManagerOptions = {
    apiKey: string;
    logError?: (message: string) => void;
};
/**
 * Obtains and refreshes the JWT used to authenticate with Kount APIs.
 *
 * Create one instance and share it across the application features that need
 * Kount API access.
 */
export declare class TokenManager {
    private static instance;
    private accessToken;
    private expiresAt;
    private readonly apiKey;
    private readonly logError;
    private constructor();
    static getInstance(options: TokenManagerOptions): TokenManager;
    getAccessToken(): Promise<string>;
    private refreshToken;
    private requestAccessToken;
    private refreshTokenLoop;
}
