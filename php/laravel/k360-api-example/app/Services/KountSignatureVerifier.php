<?php

namespace App\Services;

use Illuminate\Support\Facades\Log;
use Carbon\Carbon;
use Exception;
use InvalidArgumentException;
use RuntimeException;
use phpseclib3\Crypt\PublicKeyLoader;
use phpseclib3\Crypt\RSA;

class KountSignatureVerifier
{
    private int $gracePeriodSeconds;

    public function __construct(int $gracePeriodSeconds = 300)
    {
        $this->gracePeriodSeconds = $gracePeriodSeconds;
    }

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
        Log::channel('kount')->warning($publicKeyBase64);


        if (empty($publicKeyBase64)) {
            throw new RuntimeException("KOUNT_PUBLIC_KEY is not configured.");
        }

        // phpseclib is smart enough to read the raw DER binary without us building a PEM string
        $publicKeyDer = base64_decode($publicKeyBase64, true);
        if ($publicKeyDer === false) {
            throw new RuntimeException("Invalid base64 encoding in public key.");
        }

        // 3. Parse and validate timestamp
        try {
            $timestamp = Carbon::parse($timestampIso8601)->timezone('UTC');
        } catch (Exception $e) {
            throw new InvalidArgumentException("Invalid timestamp format.");
        }

        $now = $nowOverride ?? Carbon::now('UTC');
        $deltaSeconds = $now->diffInSeconds($timestamp, false);

        if ($deltaSeconds > $this->gracePeriodSeconds) {
            throw new InvalidArgumentException("Timestamp too old.");
        }
        if ($deltaSeconds < -$this->gracePeriodSeconds) {
            throw new InvalidArgumentException("Timestamp too new.");
        }

        // 4. Combine timestamp and payload to create the digest
        $digest = $timestampIso8601 . $payload;

        // 5. Verify signature using RSA-PSS via phpseclib
        try {
            /** @var \phpseclib3\Crypt\RSA\PublicKey $rsa */
            $rsa = PublicKeyLoader::load($publicKeyDer);

            // Configure the exact same parameters as C#
            $rsa = $rsa->withHash('sha256')
                       ->withMGFHash('sha256')
                       ->withPadding(RSA::SIGNATURE_PSS);

            $isValid = $rsa->verify($digest, $signature);

            if (!$isValid) {
                Log::channel('kount')->warning("Signature verification failed: invalid signature.");
                throw new InvalidArgumentException("Signature verification failed.");
            }

            Log::channel('kount')->info("Signature successfully verified.");
            return true;

        } catch (Exception $e) {
            Log::channel('kount')->error("Signature verification failed: " . $e->getMessage());
            throw new InvalidArgumentException("Signature verification failed.");
        }
    }
}
