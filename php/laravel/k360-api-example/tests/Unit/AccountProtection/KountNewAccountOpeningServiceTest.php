<?php

namespace Tests\Unit\AccountProtection;

use App\Services\AccountProtection\KountNewAccountOpeningService;
use App\Services\KountTokenService;
use Illuminate\Http\Client\Request;
use Illuminate\Support\Facades\Http;
use Mockery;
use Tests\TestCase;

class KountNewAccountOpeningServiceTest extends TestCase
{
    public function test_it_posts_nao_v2_with_the_existing_jwt_and_wraps_the_decision(): void
    {
        config(['services.kount.api_base_url' => 'https://api-sandbox.kount.test']);
        Http::fake([
            'api-sandbox.kount.test/*' => Http::response(
                ['decision' => 'CHALLENGE', 'deviceId' => 'device-1'],
                200,
                ['X-Correlation-Id' => '2438ac3c-37eb-4902-adef-ed16b4431030'],
            ),
        ]);

        $tokenService = Mockery::mock(KountTokenService::class);
        $tokenService->shouldReceive('getValidToken')->once()->andReturn('existing-jwt');

        $service = new KountNewAccountOpeningService($tokenService);
        $result = $service->submit([
            'inquiryId' => 'nao-php-1',
            'deviceSessionId' => 'device-session-1',
            'empty' => null,
            'person' => ['emailAddress' => '', 'phoneNumber' => '+12081234567'],
            'customFields' => ['exampleBoolean' => false, 'exampleNumber' => 0],
        ]);

        $this->assertSame('CHALLENGE', $result['decision']);
        $this->assertSame('2438ac3c-37eb-4902-adef-ed16b4431030', $result['correlationId']);
        $this->assertTrue($result['challenge']);
        $this->assertFalse($result['allow']);
        $this->assertFalse($result['block']);

        Http::assertSent(fn (Request $request): bool => $request->method() === 'POST'
            && $request->url() === 'https://api-sandbox.kount.test/newaccountopening/v2'
            && $request->hasHeader('Authorization', 'Bearer existing-jwt')
            && $request->data() === [
                'inquiryId' => 'nao-php-1',
                'deviceSessionId' => 'device-session-1',
                'person' => ['phoneNumber' => '+12081234567'],
                'customFields' => ['exampleBoolean' => false, 'exampleNumber' => 0],
            ]);
    }

    public function test_it_retries_a_transient_response(): void
    {
        config(['services.kount.api_base_url' => 'https://api-sandbox.kount.test']);
        Http::fake([
            'api-sandbox.kount.test/*' => Http::sequence()
                ->push(['message' => 'temporarily unavailable'], 503)
                ->push(['decision' => 'ALLOW']),
        ]);

        $tokenService = Mockery::mock(KountTokenService::class);
        $tokenService->shouldReceive('getValidToken')->once()->andReturn('existing-jwt');

        $result = (new KountNewAccountOpeningService($tokenService))->submit([
            'inquiryId' => 'nao-php-retry',
            'deviceSessionId' => 'device-session-retry',
        ]);

        $this->assertSame('ALLOW', $result['decision']);
        Http::assertSentCount(2);
    }
}
