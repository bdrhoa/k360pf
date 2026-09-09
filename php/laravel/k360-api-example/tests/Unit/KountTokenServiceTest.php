<?php

namespace Tests\Unit;

use App\Services\KountTokenService;
use Illuminate\Http\Client\Request;
use Illuminate\Http\Client\RequestException;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class KountTokenServiceTest extends TestCase
{
    public function test_it_uses_the_configured_cache_store_without_the_application_database(): void
    {
        config([
            'services.kount.api_key' => 'example-basic-credential',
            'services.kount.cache_store' => 'array',
        ]);
        Cache::store('array')->clear();
        Http::fake([
            'login-uat.equifax.com/*' => Http::response([
                'access_token' => 'example-jwt',
                'expires_in' => 3600,
            ]),
        ]);

        $service = new KountTokenService;

        $this->assertSame('example-jwt', $service->getValidToken());
        $this->assertSame('example-jwt', $service->getValidToken());

        Http::assertSentCount(1);
        Http::assertSent(fn (Request $request): bool => $request->url() === 'https://login-uat.equifax.com/as/token'
            && $request->hasHeader('Authorization', 'Basic example-basic-credential'));
    }

    public function test_it_does_not_retry_a_rejected_credential(): void
    {
        config([
            'services.kount.api_key' => 'rejected-basic-credential',
            'services.kount.cache_store' => 'array',
        ]);
        Cache::store('array')->clear();
        Http::fake([
            'login-uat.equifax.com/*' => Http::response(['error' => 'invalid_client'], 401),
        ]);

        $this->expectException(RequestException::class);

        try {
            (new KountTokenService)->getValidToken();
        } finally {
            Http::assertSentCount(1);
        }
    }
}
