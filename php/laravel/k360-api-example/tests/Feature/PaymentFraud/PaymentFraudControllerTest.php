<?php

namespace Tests\Feature\PaymentFraud;

use App\Services\PaymentFraud\KountPaymentFraudService;
use Mockery;
use Tests\TestCase;

class PaymentFraudControllerTest extends TestCase
{
    public function test_it_evaluates_a_high_fidelity_order(): void
    {
        $service = Mockery::mock(KountPaymentFraudService::class);
        $service->shouldReceive('evaluateOrder')
            ->once()
            ->withArgs(fn (array $order, bool $excludeDevice, bool $excludeFromPaymentsModel): bool => $order['merchantOrderId'] === 'merchant-order-1'
                && $order['transactions'][0]['orderTotal'] === '6150'
                && ! $excludeDevice
                && ! $excludeFromPaymentsModel)
            ->andReturn([
                'order' => [
                    'orderId' => 'kount-order-1',
                    'riskInquiry' => ['decision' => 'APPROVE'],
                ],
            ]);
        $this->app->instance(KountPaymentFraudService::class, $service);

        $this->postJson('/api/payment-fraud/orders/evaluate', $this->evaluationPayload())
            ->assertOk()
            ->assertJsonPath('order.orderId', 'kount-order-1')
            ->assertJsonPath('order.riskInquiry.decision', 'APPROVE');
    }

    public function test_it_forwards_the_swagger_minimum_without_an_accept_header(): void
    {
        $service = Mockery::mock(KountPaymentFraudService::class);
        $service->shouldReceive('evaluateOrder')
            ->once()
            ->with(['merchantOrderId' => 'merchant-order-1001'], false, false)
            ->andReturn(['order' => ['orderId' => 'kount-order-1']]);
        $this->app->instance(KountPaymentFraudService::class, $service);

        $this->call(
            'POST',
            '/api/payment-fraud/orders/evaluate',
            server: ['CONTENT_TYPE' => 'application/json'],
            content: json_encode(['merchantOrderId' => 'merchant-order-1001'], JSON_THROW_ON_ERROR),
        )
            ->assertOk()
            ->assertJsonPath('order.orderId', 'kount-order-1');
    }

    public function test_validation_errors_are_json_without_an_accept_header(): void
    {
        $this->call(
            'POST',
            '/api/payment-fraud/orders/evaluate',
            server: ['CONTENT_TYPE' => 'application/json'],
            content: '{}',
        )
            ->assertUnprocessable()
            ->assertHeader('Content-Type', 'application/json')
            ->assertJsonValidationErrors('merchantOrderId');
    }

    public function test_it_updates_an_order_with_the_real_authorization_result(): void
    {
        $update = [
            'merchantOrderId' => 'merchant-order-1',
            'transactions' => [[
                'transactionId' => 'transaction-1',
                'authorizationStatus' => [
                    'authResult' => 'APPROVED',
                    'processorAuthCode' => '001234',
                    'processorTransactionId' => 'processor-transaction-1',
                    'verificationResponse' => [
                        'cvvStatus' => 'MATCH',
                        'avsStatus' => 'Y',
                    ],
                ],
            ]],
        ];

        $service = Mockery::mock(KountPaymentFraudService::class);
        $service->shouldReceive('updateOrder')
            ->once()
            ->with('kount-order-1', $update)
            ->andReturn(['orderId' => 'kount-order-1']);
        $this->app->instance(KountPaymentFraudService::class, $service);

        $this->patchJson('/api/payment-fraud/orders/kount-order-1', $update)
            ->assertOk()
            ->assertJsonPath('orderId', 'kount-order-1');
    }

    /**
     * @return array<string, mixed>
     */
    private function evaluationPayload(): array
    {
        return [
            'merchantOrderId' => 'merchant-order-1',
            'channel' => 'WEB',
            'deviceSessionId' => 'device-session-1',
            'creationDateTime' => '2026-09-09T18:30:00.123Z',
            'userIp' => '192.0.2.1',
            'account' => [
                'id' => 'customer-1',
                'creationDateTime' => '2024-01-10T10:15:30Z',
            ],
            'items' => [[
                'id' => 'item-1',
                'name' => 'Gaming Mouse',
                'price' => '6000',
                'quantity' => 1,
                'category' => 'Electronics',
            ]],
            'fulfillment' => [[
                'type' => 'SHIPPED',
                'merchantFulfillmentId' => 'fulfillment-1',
                'shipping' => ['provider' => 'UPS', 'method' => 'EXPRESS'],
            ]],
            'transactions' => [[
                'payment' => [
                    'type' => 'CREDIT_CARD',
                    'paymentToken' => 'KHASHED_PAYMENT_VALUE',
                    'expirationMonth' => 12,
                    'expirationYear' => 2028,
                ],
                'orderTotal' => '6150',
                'currency' => 'USD',
                'merchantTransactionId' => 'merchant-transaction-1',
                'billedPerson' => [
                    'name' => ['first' => 'Ada', 'family' => 'Lovelace'],
                    'emailAddress' => 'ada@example.com',
                    'address' => [
                        'line1' => '123 Main St',
                        'city' => 'Boise',
                        'region' => 'ID',
                        'postalCode' => '83702',
                        'countryCode' => 'US',
                    ],
                ],
            ]],
        ];
    }
}
