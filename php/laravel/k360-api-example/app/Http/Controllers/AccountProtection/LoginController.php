<?php

namespace App\Http\Controllers\AccountProtection;

use App\Http\Controllers\Controller;
use App\Services\AccountProtection\KountLoginService;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class LoginController extends Controller
{
    public function __construct(private readonly KountLoginService $login) {}

    /**
     * Build and submit a spec-shaped Login V2 demo inquiry.
     */
    public function demo(): JsonResponse
    {
        $payload = $this->buildDemoPayload();

        try {
            return response()->json($this->login->submit($payload));
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
        return [
            'inquiryId' => str_replace('-', '', Str::uuid()->toString()),
            'channel' => config('services.kount.channel', 'DEFAULT'),
            'deviceSessionId' => str_replace('-', '', Str::uuid()->toString()),
            'userIp' => '192.168.0.1',
            'loginUrl' => 'https://www.example.com/login',
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
                'id' => 'meoyyd8za8jdmwfm',
                'type' => 'VIP',
                'creationDateTime' => '2024-01-01T12:12:12.000Z',
                'username' => 'meoyyd8za8jdmwfm',
                'userPassword' => '38401eb46f8fbb74c1846a5f47f68d83a9bef126b1d4143f886cd464323cdaab',
                'accountIsActive' => true,
            ],
            'strategy' => [
                'mfaTemplateName' => 'default',
                'mfaTemplateValues' => [
                    'firstName' => 'John',
                    'accountType' => 'VIP',
                ],
            ],
            'customFields' => [
                'exampleBoolean' => true,
                'exampleNumber' => 42,
                'exampleString' => 'Login PHP demo',
            ],
        ];
    }

    private function upstreamError(RequestException $exception, string $inquiryId): JsonResponse
    {
        $correlationId = $exception->response->header('X-Correlation-Id');

        Log::channel('kount')->error('Kount Login request failed.', [
            'inquiryId' => $inquiryId,
            'status' => $exception->response->status(),
            'correlationId' => $correlationId,
        ]);

        return response()->json(array_filter([
            'error' => 'Kount Login request failed.',
            'correlationId' => $correlationId,
        ]), 502);
    }

    private function connectionError(ConnectionException $exception, string $inquiryId): JsonResponse
    {
        Log::channel('kount')->error('Could not connect to Kount Login.', [
            'inquiryId' => $inquiryId,
            'exception' => $exception->getMessage(),
        ]);

        return response()->json(['error' => 'Kount Login is unavailable.'], 503);
    }
}
