<?php

use App\Http\Controllers\AccountProtection\LoginController;
use App\Http\Controllers\AccountProtection\NewAccountOpeningController;
use App\Http\Controllers\KountWebhookController;
use App\Http\Controllers\PaymentFraud\PaymentFraudController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

Route::post('/kount360-webhook-receiver', [KountWebhookController::class, 'handle']);

// Payments Fraud
Route::post('/payment-fraud/orders/evaluate', [PaymentFraudController::class, 'evaluate']);
Route::patch('/payment-fraud/orders/{orderId}', [PaymentFraudController::class, 'update']);

// Account Protection
Route::post('/account-protection/login/demo', [LoginController::class, 'demo']);
Route::post('/account-protection/new-account-opening/demo', [NewAccountOpeningController::class, 'demo']);
