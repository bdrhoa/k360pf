<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

use App\Http\Controllers\KountWebhookController;
use App\Http\Controllers\PaymentFraudController;

Route::post('/kount360-webhook-receiver', [KountWebhookController::class, 'handle']);
Route::post('/payment-fraud/orders/evaluate', [PaymentFraudController::class, 'evaluate']);
Route::patch('/payment-fraud/orders/{orderId}', [PaymentFraudController::class, 'update']);
