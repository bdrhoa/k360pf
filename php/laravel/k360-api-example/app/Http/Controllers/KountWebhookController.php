<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;
use App\Services\KountSignatureVerifier;
use Exception;
use InvalidArgumentException;
use RuntimeException;

class KountWebhookController extends Controller
{
    private KountSignatureVerifier $signatureVerifier;

    // Laravel automatically injects the service here
    public function __construct(KountSignatureVerifier $signatureVerifier)
    {
        $this->signatureVerifier = $signatureVerifier;
    }

    /**
     * Handles incoming Kount Webhooks
     */
    public function handle(Request $request): JsonResponse
    {
        $timestampHeader = $request->header('X-Event-Timestamp');
        $signatureHeader = $request->header('X-Event-Signature');

        if (empty($timestampHeader)) {
            return response()->json(['error' => 'Missing X-Event-Timestamp header'], 400);
        }

        if (empty($signatureHeader)) {
            return response()->json(['error' => 'Missing X-Event-Signature header'], 400);
        }

        // In Laravel, $request->getContent() gets the raw HTTP body string perfectly
        $body = $request->getContent();

        Log::channel('kount')->info("Raw request body: {$body}");
        Log::channel('kount')->info("X-Event-Timestamp: {$timestampHeader}");
        Log::channel('kount')->info("X-Event-Signature: {$signatureHeader}");

        if (empty(trim($body))) {
            return response()->json(['error' => 'Empty request body'], 500);
        }

        // 1. Verify Signature
        try {
            // Log digest for test reconstruction (optional, matching your C# code)
            $digestBase64 = base64_encode($timestampHeader . $body);
            Log::channel('kount')->info("Digest base64 for test reconstruction: {$digestBase64}");

            // Verify
            $this->signatureVerifier->verify($signatureHeader, $timestampHeader, $body);

        } catch (InvalidArgumentException $ex) {
            Log::channel('kount')->error("Signature verification error: {$ex->getMessage()}");
            return response()->json(['error' => $ex->getMessage()], 400);
        } catch (RuntimeException $ex) {
            Log::channel('kount')->error("Public key error: {$ex->getMessage()}");
            return response()->json(['error' => $ex->getMessage()], 500);
        }

        // 2. Process Payload
        try {
            // Laravel parses JSON easily without needing to cast elements
            $payload = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
            
            $newValue = $payload['newValue'] ?? null;

            if ($newValue === "DECLINE") {
                Log::channel('kount')->info("Simulated order cancellation");
            } elseif ($newValue === "APPROVE") {
                Log::channel('kount')->info("Simulated order processing");
            } else {
                Log::channel('kount')->error("Unexpected newValue: {$newValue}");
            }

        } catch (\JsonException $ex) {
            Log::channel('kount')->error("Invalid JSON payload: {$ex->getMessage()}");
            return response()->json(['error' => 'Invalid JSON payload'], 400);
        }

        // 3. Return Success
        return response()->json(['Status' => 'ok'], 200);
    }
}