<?php

namespace Tests\Unit;

use App\Services\KountPaymentFraudService;
use App\Services\KountTokenService;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Mockery;
use Tests\TestCase;

class KountPaymentFraudServiceTest extends TestCase
{
    public function test_it_evaluates_an_order_with_the_existing_jwt_service(): void
    {
        config(['services.kount.api_base_url' => 'https://api-sandbox.kount.test']);
        Http::fake([
            'api-sandbox.kount.test/*' => Http::response([
                'order' => [
                    'orderId' => 'kount-order-1',
                    'riskInquiry' => ['decision' => 'APPROVE'],
                ],
            ]),
        ]);

        $tokenService = Mockery::mock(KountTokenService::class);
        $tokenService->shouldReceive('getValidToken')->once()->andReturn('existing-jwt');

        $service = new KountPaymentFraudService($tokenService);
        $result = $service->evaluateOrder([
            'merchantOrderId' => 'merchant-order-1',
            'empty' => null,
            'account' => ['username' => '', 'accountIsActive' => false],
            'transactions' => [['orderTotal' => '0', 'optional' => []]],
        ], excludeFromPaymentsModel: true);

        $this->assertSame('APPROVE', $result['order']['riskInquiry']['decision']);
        Http::assertSent(function (Request $request): bool {
            return $request->method() === 'POST'
                && str_starts_with($request->url(), 'https://api-sandbox.kount.test/commerce/v2/orders?')
                && str_contains($request->url(), 'riskInquiry=true')
                && str_contains($request->url(), 'excludeDevice=false')
                && str_contains($request->url(), 'excludeFromPaymentsModel=true')
                && $request->hasHeader('Authorization', 'Bearer existing-jwt')
                && $request->data() === [
                    'merchantOrderId' => 'merchant-order-1',
                    'account' => ['accountIsActive' => false],
                    'transactions' => [['orderTotal' => '0']],
                ];
        });
    }

    public function test_it_updates_the_url_encoded_order_with_lifecycle_data(): void
    {
        config(['services.kount.api_base_url' => 'https://api-sandbox.kount.test/']);
        Http::fake([
            'api-sandbox.kount.test/*' => Http::response(['orderId' => 'kount/order 1']),
        ]);

        $tokenService = Mockery::mock(KountTokenService::class);
        $tokenService->shouldReceive('getValidToken')->once()->andReturn('existing-jwt');

        $service = new KountPaymentFraudService($tokenService);
        $service->updateOrder('kount/order 1', [
            'transactions' => [[
                'transactionId' => 'transaction-1',
                'authorizationStatus' => [
                    'authResult' => 'APPROVED',
                    'processorAuthCode' => '001234',
                ],
            ]],
        ]);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'PATCH'
            && $request->url() === 'https://api-sandbox.kount.test/commerce/v2/orders/kount%2Forder%201'
            && $request->hasHeader('Authorization', 'Bearer existing-jwt'));
    }
}
