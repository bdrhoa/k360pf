<?php

namespace App\Http\Controllers\AccountProtection;

use App\Http\Controllers\Controller;
use App\Services\AccountProtection\KountNewAccountOpeningService;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class NewAccountOpeningController extends Controller
{
    public function __construct(private readonly KountNewAccountOpeningService $newAccountOpening) {}

    /**
     * Build and submit a spec-shaped New Account Opening V2 demo inquiry.
     */
    public function demo(): JsonResponse
    {
        $payload = $this->buildDemoPayload();

        try {
            return response()->json($this->newAccountOpening->submit($payload));
        } catch (RequestException $exception) {
            return $this->upstreamError($exception, $payload['inquiryId']);
        } catch (ConnectionException $exception) {
            return $this->connectionError($exception, $payload['inquiryId']);
        }
    }

    /**
     * @return array<string, mixed>
     */
    private function buildDemoPayload(): array
    {
        $deviceSessionId = str_replace('-', '', Str::uuid()->toString());
        $payload = [
            'inquiryId' => 'nao-php-'.Str::uuid()->toString(),
            'channel' => config('services.kount.channel', 'DEFAULT'),
            'deviceSessionId' => $deviceSessionId,
            'userIp' => '192.168.0.1',
            'accountCreationUrl' => 'https://www.example.com/create-account',
            'person' => [
                'name' => [
                    'first' => 'John',
                    'last' => 'Doe',
                    'preferred' => 'Johnny',
                ],
                'emailAddress' => 'john.doe@example.com',
                'phoneNumber' => '+12081234567',
                'addresses' => [[
                    'line1' => '5813-5849 Quail Meadows Dr',
                    'city' => 'Poplar Bluff',
                    'region' => 'CO',
                    'postalCode' => '63901-0000',
                    'countryCode' => 'US',
                    'addressType' => 'BILLING',
                ]],
            ],
            'account' => [
                'id' => '11223dr44',
                'type' => 'VIP',
                'username' => 'meoyyd8za8jdmwfm',
            ],
            'strategy' => [
                'verificationTemplateName' => 'default',
                'verificationTemplateValues' => [
                    'firstName' => 'John',
                    'accountType' => 'VIP',
                ],
            ],
            'customFields' => [
                'exampleBoolean' => true,
                'exampleNumber' => 42,
                'exampleString' => 'NAO PHP demo',
            ],
        ];

        $clientId = config('services.kount.client_id');
        if (is_string($clientId) && $clientId !== '') {
            $payload['sharedContext'] = [
                'sourceClientId' => $clientId,
                'sourceDeviceSessionId' => $deviceSessionId,
            ];
        }

        return $payload;
    }

    private function upstreamError(RequestException $exception, string $inquiryId): JsonResponse
    {
        $correlationId = $exception->response->header('X-Correlation-Id');

        Log::channel('kount')->error('Kount New Account Opening request failed.', [
            'inquiryId' => $inquiryId,
            'status' => $exception->response->status(),
            'correlationId' => $correlationId,
        ]);

        return response()->json(array_filter([
            'error' => 'Kount New Account Opening request failed.',
            'correlationId' => $correlationId,
        ]), 502);
    }

    private function connectionError(ConnectionException $exception, string $inquiryId): JsonResponse
    {
        Log::channel('kount')->error('Could not connect to Kount New Account Opening.', [
            'inquiryId' => $inquiryId,
            'exception' => $exception->getMessage(),
        ]);

        return response()->json(['error' => 'Kount New Account Opening is unavailable.'], 503);
    }
}
