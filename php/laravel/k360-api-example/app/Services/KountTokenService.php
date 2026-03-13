<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;
use Illuminate\Http\Client\RequestException;
use Exception;

class KountTokenService
{
    private string $authUrl;
    private string $apiKey;
    
    // Cache keys
    private const CACHE_KEY_TOKEN = 'kount_access_token';
    private const CACHE_KEY_EXPIRES = 'kount_token_expires_at';
    private const LOCK_KEY = 'kount_token_refresh_lock';

    // 2 minutes in seconds
    private const REFRESH_BUFFER_SECONDS = 120; 

    public function __construct()
    {
        $this->authUrl = 'https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token';
        
        // Pulls from config/services.php or directly from env()
        $this->apiKey = config('services.kount.api_key'); 

        if (empty($this->apiKey)) {
            throw new Exception("KOUNT_API_KEY is not configured.");
        }
    }

    /**
     * Retrieves a valid access token, refreshing it if near expiry.
     */
    public function getValidToken(): string
    {
        if (!$this->needsRefresh()) {
            return Cache::get(self::CACHE_KEY_TOKEN);
        }

        // Laravel's equivalent of SemaphoreSlim. Wait up to 5 seconds to get a lock.
        $lock = Cache::lock(self::LOCK_KEY, 10);

        try {
            $lock->block(5); // Block execution until lock is acquired

            // Double-check pattern: Another request might have refreshed it while we waited
            if (!$this->needsRefresh()) {
                return Cache::get(self::CACHE_KEY_TOKEN);
            }

            return $this->refreshToken();
            
        } catch (\Illuminate\Contracts\Cache\LockTimeoutException $e) {
            Log::error("Failed to acquire lock for Kount token refresh.");
            throw new Exception("Could not acquire lock to refresh Kount token.");
        } finally {
            $lock?->release();
        }
    }

    /**
     * Checks if the token is missing or within the 2-minute buffer.
     */
    private function needsRefresh(): bool
    {
        $token = Cache::get(self::CACHE_KEY_TOKEN);
        $expiresAt = Cache::get(self::CACHE_KEY_EXPIRES);

        if (!$token || !$expiresAt) {
            return true;
        }

        // Check if current time + buffer is greater than or equal to expiration
        return now()->addSeconds(self::REFRESH_BUFFER_SECONDS)->greaterThanOrEqualTo($expiresAt);
    }

    /**
     * Fetches a new token from the Kount authentication server.
     * Uses exponential backoff with full jitter for retries.
     */
    private function refreshToken(): string
    {
        Log::info("Refreshing Kount access token...");

        $response = Http::withToken($this->apiKey, 'Basic')
            ->asForm()
            ->acceptJson()
            ->retry(3, function (int $attempt, Exception $exception) {
                // Don't retry if it's a hard auth failure
                if ($exception instanceof RequestException && $exception->response->clientError()) {
                    return false; 
                }

                // Exponential base: e.g., 100ms, 200ms, 400ms
                $exponentialDelay = (2 ** $attempt) * 50; 
                
                // Add Full Jitter: Randomize the delay between 0 and the exponential max
                return random_int(0, $exponentialDelay);
            })
            ->post($this->authUrl, [
                'grant_type' => 'client_credentials',
                'scope' => 'k1_integration_api'
            ]);

        if ($response->failed()) {
            Log::error("Kount API Token Refresh Failed", ['status' => $response->status(), 'body' => $response->body()]);
            $response->throw();
        }

        $json = $response->json();
        Log::info("Received token response.", ['response' => $json]);

        if (empty($json['access_token']) || empty($json['expires_in'])) {
            throw new Exception("Invalid token response from Kount API");
        }

        $token = $json['access_token'];
        $expiresIn = (int) $json['expires_in'];
        $expirationTime = now()->addSeconds($expiresIn);

        // Store in Cache indefinitely (or for the actual duration) since we manage the expiration manually
        Cache::put(self::CACHE_KEY_TOKEN, $token);
        Cache::put(self::CACHE_KEY_EXPIRES, $expirationTime);

        Log::info("Token successfully refreshed, expires at {$expirationTime->toDateTimeString()}");

        return $token;
    }
}