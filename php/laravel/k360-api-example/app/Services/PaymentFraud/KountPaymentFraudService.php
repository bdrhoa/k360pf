<?php

namespace App\Services\PaymentFraud;

use App\Services\KountTokenService;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\PendingRequest;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Http;

class KountPaymentFraudService
{
    public function __construct(private readonly KountTokenService $tokenService) {}

    /**
     * Evaluate an order and request a Payments Fraud risk inquiry.
     *
     * @return array<string, mixed>
     */
    public function evaluateOrder(
        array $order,
        bool $excludeDevice = false,
        bool $excludeFromPaymentsModel = false,
    ): array {
        $response = $this->client()
            ->withQueryParameters([
                'riskInquiry' => 'true',
                'excludeDevice' => $excludeDevice ? 'true' : 'false',
                'excludeFromPaymentsModel' => $excludeFromPaymentsModel ? 'true' : 'false',
            ])
            ->post($this->ordersUrl(), $this->withoutEmptyValues($order));

        $response->throw();

        return $response->json();
    }

    /**
     * Add post-authorization or later lifecycle data to an existing order.
     *
     * @return array<string, mixed>
     */
    public function updateOrder(string $orderId, array $update): array
    {
        $response = $this->client()->patch(
            $this->ordersUrl().'/'.rawurlencode($orderId),
            $this->withoutEmptyValues($update),
        );

        $response->throw();

        return $response->json();
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

    private function ordersUrl(): string
    {
        return rtrim((string) config('services.kount.api_base_url'), '/')
            .'/commerce/v2/orders';
    }

    /**
     * Kount recommends omitting properties that have no value. Keep meaningful
     * false and zero values while removing nulls, blank strings, and empty arrays.
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
