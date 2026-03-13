<?php

namespace App\Services;

use Illuminate\Support\Facades\Log;
use Carbon\Carbon;
use Exception;
use InvalidArgumentException;
use RuntimeException;

class KountSignatureVerifier
{
    private int $gracePeriodSeconds;

    public function __construct(int $gracePeriodSeconds = 300) // 5 minutes default
    {
        $this->gracePeriodSeconds = $gracePeriodSeconds;
    }

    /**
     * Verifies the Kount webhook signature using RSA-PSS.
     *
     * @param string $signatureBase64
     * @param string $timestampIso8601
     * @param string $payload (The raw JSON string)
     * @param Carbon|null $nowOverride (For testing)
     * @return bool
     * @throws Exception
     */
    public function verify(string $signatureBase64, string $timestampIso8601, string $payload, ?Carbon $nowOverride = null): bool
    {
        // 1. Validate and decode signature
        if (empty($signatureBase64)) {
            throw new InvalidArgumentException("Missing signature.");
        }

        $signature = base64_decode($signatureBase64, true);
        if ($signature === false) {
            throw new InvalidArgumentException("Invalid base64 encoding in signature.");
        }

        // 2. Get public key from environment
        $publicKeyBase64 = config('services.kount.public_key');
        if (empty($publicKeyBase64)) {
            throw new RuntimeException("KOUNT_PUBLIC_KEY is not configured.");
        }

        $publicKeyDer = base64_decode($publicKeyBase64, true);
        if ($publicKeyDer === false) {
            throw new RuntimeException("Invalid base64 encoding in public key.");
        }

        // PHP's openssl_verify requires PEM format, not raw DER. 
        // We must wrap the DER base64 in the standard PEM header/footer.
        $publicKeyPem = "-----BEGIN PUBLIC KEY-----\n" . chunk_split($publicKeyBase64, 64, "\n") . "-----END PUBLIC KEY-----\n";

        // 3. Parse and validate timestamp
        try {
            $timestamp = Carbon::parse($timestampIso8601)->timezone('UTC');
        } catch (Exception $e) {
            throw new InvalidArgumentException("Invalid timestamp format.");
        }

        $now = $nowOverride ?? Carbon::now('UTC');
        $deltaSeconds = $now->diffInSeconds($timestamp, false); // false = return negative if timestamp is in future

        // $deltaSeconds is positive if timestamp is in the past, negative if in the future
        if ($deltaSeconds > $this->gracePeriodSeconds) {
            throw new InvalidArgumentException("Timestamp too old.");
        }
        if ($deltaSeconds < -$this->gracePeriodSeconds) {
            throw new InvalidArgumentException("Timestamp too new.");
        }

        // 4. Combine timestamp and payload to create the digest
        $digest = $timestampIso8601 . $payload;

        // 5. Verify signature using RSA-PSS
        // openssl_verify handles the hashing (SHA256) and decryption in one step
        $isValid = openssl_verify(
            $digest, 
            $signature, 
            $publicKeyPem, 
            OPENSSL_ALGO_SHA256
        );

        if ($isValid === 1) {
            Log::channel('kount')->info("Signature successfully verified.");
            return true;
        }

        if ($isValid === 0) {
            Log::channel('kount')->warning("Signature verification failed: invalid signature.");
            throw new InvalidArgumentException("Signature verification failed.");
        }

        // $isValid === -1 means an error occurred during the crypto operation
        Log::channel('kount')->error("Signature verification failed: Cryptographic error.", [
            'openssl_error' => openssl_error_string()
        ]);
        throw new InvalidArgumentException("Signature verification failed.");
    }
}