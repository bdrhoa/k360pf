<?php

namespace App\Services\AccountProtection;

use App\Services\KountTokenService;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;

class KountNewAccountOpeningService
{
    public function __construct(private readonly KountTokenService $tokenService) {}

    /**
     * Submit a New Account Opening V2 inquiry.
     *
     * @return array{
     *     body: array<string, mixed>,
     *     decision: mixed,
     *     correlationId: ?string,
     *     challenge: bool,
     *     allow: bool,
     *     block: bool
     * }
     */
    public function submit(array $payload): array
    {
        $response = $this->client()->post(
            $this->newAccountOpeningUrl(),
            $this->withoutEmptyValues($payload),
        );

        $response->throw();

        $body = $response->json();
        $body = is_array($body) ? $body : [];
        $decision = $body['decision'] ?? null;
        $normalizedDecision = is_string($decision) ? strtoupper($decision) : null;

        return [
            'body' => $body,
            'decision' => $decision,
            'correlationId' => $response->header('X-Correlation-Id'),
            'challenge' => $normalizedDecision === 'CHALLENGE',
            'allow' => $normalizedDecision === 'ALLOW',
            'block' => $normalizedDecision === 'BLOCK',
        ];
    }

    private function client(): PendingRequest
    {
        return Http::withToken($this->tokenService->getValidToken())
            ->acceptJson()
            ->asJson()
            ->timeout((int) config('services.kount.timeout_seconds', 10))
            ->connectTimeout((int) config('services.kount.connect_timeout_seconds', 3))
            ->retry(
                3,
                fn (int $attempt): int => random_int(0, (2 ** $attempt) * 100),
                function (\Exception $exception): bool {
                    if ($exception instanceof ConnectionException) {
                        return true;
                    }

                    return $exception instanceof RequestException
                        && in_array($exception->response->status(), [403, 408, 429, 500, 502, 503, 504], true);
                },
                throw: false,
            );
    }

    private function newAccountOpeningUrl(): string
    {
        return rtrim((string) config('services.kount.api_base_url'), '/')
            .'/newaccountopening/v2';
    }

    /**
     * Omit values that are not populated while preserving meaningful false and zero values.
     *
     * @return array<mixed>
     */
    private function withoutEmptyValues(array $values): array
    {
        $cleaned = [];

        foreach ($values as $key => $value) {
            if (is_array($value)) {
                $value = $this->withoutEmptyValues($value);
            }

            if ($value === null || $value === '' || $value === []) {
                continue;
            }

            $cleaned[$key] = $value;
        }

        return $cleaned;
    }
}
