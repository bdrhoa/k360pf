<?php

namespace Tests\Feature\AccountProtection;

use App\Services\AccountProtection\KountLoginService;
use Mockery;
use Tests\TestCase;

class LoginControllerTest extends TestCase
{
    public function test_it_submits_a_spec_shaped_login_demo_inquiry(): void
    {
        config(['services.kount.channel' => 'PHP_WEB']);

        $service = Mockery::mock(KountLoginService::class);
        $service->shouldReceive('submit')
            ->once()
            ->withArgs(function (array $payload): bool {
                return preg_match('/^[a-f0-9]{32}$/', $payload['inquiryId']) === 1
                    && $payload['channel'] === 'PHP_WEB'
                    && strlen($payload['deviceSessionId']) === 32
                    && $payload['loginUrl'] === 'https://www.example.com/login'
                    && $payload['person']['emailAddress'] === 'john.doe@example.com'
                    && $payload['account']['id'] === 'meoyyd8za8jdmwfm'
                    && $payload['account']['username'] === 'meoyyd8za8jdmwfm'
                    && $payload['account']['accountIsActive'] === true
                    && $payload['strategy']['mfaTemplateName'] === 'default';
            })
            ->andReturn([
                'body' => ['decision' => 'ALLOW'],
                'decision' => 'ALLOW',
                'correlationId' => '2438ac3c-37eb-4902-adef-ed16b4431030',
                'challenge' => false,
                'allow' => true,
                'block' => false,
            ]);
        $this->app->instance(KountLoginService::class, $service);

        $this->postJson('/api/account-protection/login/demo')
            ->assertOk()
            ->assertJsonPath('decision', 'ALLOW')
            ->assertJsonPath('correlationId', '2438ac3c-37eb-4902-adef-ed16b4431030')
            ->assertJsonPath('allow', true);
    }
}
