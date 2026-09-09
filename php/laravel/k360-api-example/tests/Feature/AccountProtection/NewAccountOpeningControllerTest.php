<?php

namespace Tests\Feature\AccountProtection;

use App\Services\AccountProtection\KountNewAccountOpeningService;
use Mockery;
use Tests\TestCase;

class NewAccountOpeningControllerTest extends TestCase
{
    public function test_it_submits_a_spec_shaped_nao_demo_inquiry(): void
    {
        config([
            'services.kount.channel' => 'PHP_WEB',
            'services.kount.client_id' => 'client123',
        ]);

        $service = Mockery::mock(KountNewAccountOpeningService::class);
        $service->shouldReceive('submit')
            ->once()
            ->withArgs(function (array $payload): bool {
                return str_starts_with($payload['inquiryId'], 'nao-php-')
                    && $payload['channel'] === 'PHP_WEB'
                    && strlen($payload['deviceSessionId']) === 32
                    && $payload['person']['emailAddress'] === 'john.doe@example.com'
                    && $payload['account']['id'] === '11223dr44'
                    && $payload['strategy']['verificationTemplateName'] === 'default'
                    && $payload['sharedContext']['sourceClientId'] === 'client123'
                    && $payload['sharedContext']['sourceDeviceSessionId'] === $payload['deviceSessionId'];
            })
            ->andReturn([
                'body' => ['decision' => 'ALLOW'],
                'decision' => 'ALLOW',
                'correlationId' => '2438ac3c-37eb-4902-adef-ed16b4431030',
                'challenge' => false,
                'allow' => true,
                'block' => false,
            ]);
        $this->app->instance(KountNewAccountOpeningService::class, $service);

        $this->postJson('/api/account-protection/new-account-opening/demo')
            ->assertOk()
            ->assertJsonPath('decision', 'ALLOW')
            ->assertJsonPath('correlationId', '2438ac3c-37eb-4902-adef-ed16b4431030')
            ->assertJsonPath('allow', true);
    }
}
