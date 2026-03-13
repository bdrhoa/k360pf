<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

use App\Http\Controllers\KountWebhookController;

Route::post('/kount360-webhook-receiver', [KountWebhookController::class, 'handle']);