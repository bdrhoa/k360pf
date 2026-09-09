<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],
    'kount' => [
        'api_key' => env('KOUNT_API_KEY'),
        'public_key' => env('KOUNT_PUBLIC_KEY'),
        'cache_store' => env('KOUNT_CACHE_STORE', 'file'),
        'api_base_url' => env('KOUNT_API_BASE_URL', 'https://api-sandbox.kount.com'),
        'timeout_seconds' => env('KOUNT_API_TIMEOUT_SECONDS', 10),
        'connect_timeout_seconds' => env('KOUNT_API_CONNECT_TIMEOUT_SECONDS', 3),
    ],

];
