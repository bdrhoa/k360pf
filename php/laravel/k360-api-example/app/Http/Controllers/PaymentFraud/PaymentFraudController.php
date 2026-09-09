<?php

namespace App\Http\Controllers\PaymentFraud;

use App\Http\Controllers\Controller;
use App\Services\PaymentFraud\KountPaymentFraudService;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\RequestException;
use Illuminate\Http\Exceptions\HttpResponseException;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Validator;
use Illuminate\Validation\Rule;

class PaymentFraudController extends Controller
{
    public function __construct(private readonly KountPaymentFraudService $paymentFraud) {}

    /**
     * Submit a pre- or post-authorization order for a Payments Fraud decision.
     */
    public function evaluate(Request $request): JsonResponse
    {
        $excludeDevice = $request->boolean('excludeDevice');
        $excludeFromPaymentsModel = $request->boolean('excludeFromPaymentsModel');
        $order = $this->validateEvaluation($request->json()->all());

        try {
            return response()->json($this->paymentFraud->evaluateOrder(
                $order,
                $excludeDevice,
                $excludeFromPaymentsModel,
            ));
        } catch (RequestException $exception) {
            return $this->upstreamError($exception, 'evaluate', $order['merchantOrderId']);
        } catch (ConnectionException $exception) {
            return $this->connectionError($exception, 'evaluate', $order['merchantOrderId']);
        }
    }

    /**
     * Supply the real processor result or other newly available lifecycle data.
     */
    public function update(Request $request, string $orderId): JsonResponse
    {
        $update = $this->validateUpdate($request->json()->all());

        try {
            return response()->json($this->paymentFraud->updateOrder($orderId, $update));
        } catch (RequestException $exception) {
            return $this->upstreamError($exception, 'update', $update['merchantOrderId'] ?? null);
        } catch (ConnectionException $exception) {
            return $this->connectionError($exception, 'update', $update['merchantOrderId'] ?? null);
        }
    }

    /**
     * @return array<string, mixed>
     */
    private function validateUpdate(array $input): array
    {
        $validator = Validator::make($input, [
            'merchantOrderId' => ['sometimes', 'string', 'max:255'],
            'deviceSessionId' => ['sometimes', 'string', 'max:255'],
            'transactions' => ['sometimes', 'array', 'min:1'],
            'transactions.*.transactionId' => ['required_with:transactions', 'string', 'max:255'],
            'transactions.*.payment' => ['sometimes', 'array'],
            'transactions.*.payment.type' => ['sometimes', 'string', 'max:50'],
            'transactions.*.payment.paymentToken' => ['sometimes', 'string', 'max:255'],
            'transactions.*.payment.bin' => ['sometimes', 'string', 'max:8'],
            'transactions.*.payment.last4' => ['sometimes', 'string', 'size:4'],
            'transactions.*.payment.expirationMonth' => ['sometimes', 'integer', 'between:1,12'],
            'transactions.*.payment.expirationYear' => ['sometimes', 'integer', 'min:2000'],
            'transactions.*.authorizationStatus' => ['sometimes', 'array'],
            'transactions.*.authorizationStatus.authResult' => [
                'required_with:transactions.*.authorizationStatus',
                Rule::in(['APPROVED', 'DECLINED', 'ERROR', 'UNKNOWN']),
            ],
            'transactions.*.authorizationStatus.verificationResponse.cvvStatus' => [
                'sometimes',
                Rule::in(['MATCH', 'NO_MATCH', 'UNKNOWN']),
            ],
            'transactions.*.authorizationStatus.verificationResponse.avsStatus' => [
                'sometimes',
                Rule::in(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']),
            ],
            'transactions.*.authorizationStatus.processorAuthCode' => ['sometimes', 'string', 'max:255'],
            'transactions.*.authorizationStatus.processorTransactionId' => ['sometimes', 'string', 'max:255'],
            'transactions.*.authorizationStatus.acquirerReferenceNumber' => ['sometimes', 'string', 'size:23'],
            'transactions.*.authorizationStatus.gateway.id' => ['sometimes', 'string', 'max:255'],
            'transactions.*.authorizationStatus.gateway.response' => ['sometimes', 'string', 'max:255'],
            'fulfillment' => ['sometimes', 'array'],
            'fulfillment.*.fulfillmentId' => ['required_with:fulfillment', 'string', 'max:255'],
            'fulfillment.*.status' => ['sometimes', Rule::in(['PENDING', 'UNFULFILLED', 'ON_HOLD', 'FULFILLED', 'SCHEDULED', 'PARTIALLY_FULFILLED', 'DELAYED', 'CANCELED'])],
            'fulfillment.*.shipping.trackingNumber' => ['sometimes', 'string', 'max:255'],
            'fulfillment.*.shipping.provider' => ['sometimes', 'string', 'max:255'],
            'fulfillment.*.shipping.method' => ['sometimes', Rule::in(['STANDARD', 'EXPRESS', 'SAME_DAY', 'NEXT_DAY', 'SECOND_DAY'])],
            'fulfillment.*.shipping.shippedDateTime' => ['sometimes', 'date', 'regex:/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/'],
            'fulfillment.*.shipping.deliveredDateTime' => ['sometimes', 'date', 'regex:/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/'],
            'userIp' => ['sometimes', 'ip'],
            'merchantCategoryCode' => ['sometimes', 'integer'],
        ]);

        $validator->after(function ($validator) use ($input): void {
            if ($input === []) {
                $validator->errors()->add('order', 'Provide at least one order property to update.');
            }
        });

        if ($validator->fails()) {
            $this->throwJsonValidationException($validator->errors()->toArray());
        }

        return $input;
    }

    /**
     * Require the API's schema-required field and validate recommended fields when supplied.
     *
     * @return array<string, mixed>
     */
    private function validateEvaluation(array $input): array
    {
        $validator = Validator::make($input, [
            'merchantOrderId' => ['required', 'string', 'max:255'],
            'deviceSessionId' => ['sometimes', 'string', 'max:255'],
            'channel' => ['sometimes', 'string', 'max:255'],
            'creationDateTime' => ['sometimes', 'date', 'regex:/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/'],
            'userIp' => ['sometimes', 'ipv4'],
            'account.id' => ['sometimes', 'string', 'max:255'],
            'account.creationDateTime' => ['sometimes', 'date', 'regex:/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:Z|[+-]\d{2}:\d{2})$/'],
            'items' => ['sometimes', 'array', 'min:1'],
            'items.*.id' => ['sometimes', 'string', 'max:255'],
            'items.*.name' => ['sometimes', 'string', 'max:255'],
            'items.*.price' => ['sometimes', 'regex:/^\d+$/'],
            'items.*.quantity' => ['sometimes', 'integer', 'min:1'],
            'items.*.category' => ['sometimes', 'string', 'max:255'],
            'fulfillment' => ['sometimes', 'array', 'min:1'],
            'fulfillment.*.type' => ['sometimes', Rule::in(['SHIPPED', 'DIGITAL', 'STORE_PICK_UP', 'LOCAL_DELIVERY', 'STORE_DRIVE_UP', 'IN_PERSON'])],
            'fulfillment.*.merchantFulfillmentId' => ['sometimes', 'string', 'max:255'],
            'transactions' => ['sometimes', 'array', 'min:1'],
            'transactions.*.payment' => ['sometimes', 'array'],
            'transactions.*.payment.type' => ['sometimes', 'string', 'max:50'],
            'transactions.*.payment.paymentToken' => ['sometimes', 'string', 'max:255'],
            'transactions.*.payment.bin' => ['sometimes', 'string', 'max:8'],
            'transactions.*.payment.last4' => ['sometimes', 'string', 'size:4'],
            'transactions.*.payment.expirationMonth' => ['sometimes', 'integer', 'between:1,12'],
            'transactions.*.payment.expirationYear' => ['sometimes', 'integer', 'min:2000'],
            'transactions.*.orderTotal' => ['sometimes', 'regex:/^\d+$/'],
            'transactions.*.currency' => ['sometimes', 'string', 'size:3'],
            'transactions.*.billedPerson.emailAddress' => ['sometimes', 'email:rfc'],
            'transactions.*.billedPerson.name.first' => ['sometimes', 'string', 'max:255'],
            'transactions.*.billedPerson.name.family' => ['sometimes', 'string', 'max:255'],
            'transactions.*.billedPerson.address.line1' => ['sometimes', 'string', 'max:255'],
            'transactions.*.billedPerson.address.city' => ['sometimes', 'string', 'max:255'],
            'transactions.*.billedPerson.address.region' => ['sometimes', 'string', 'max:255'],
            'transactions.*.billedPerson.address.postalCode' => ['sometimes', 'string', 'max:32'],
            'transactions.*.billedPerson.address.countryCode' => ['sometimes', 'string', 'size:2'],
            'transactions.*.merchantTransactionId' => ['sometimes', 'string', 'max:255'],
            'transactions.*.authorizationStatus.authResult' => ['sometimes', Rule::in(['APPROVED', 'DECLINED', 'ERROR', 'UNKNOWN'])],
            'merchantCategoryCode' => ['sometimes', 'integer'],
            'merchant.name' => ['sometimes', 'string', 'max:255'],
            'merchant.id' => ['sometimes', 'string', 'max:255'],
            'customFields' => ['sometimes', 'array'],
        ]);

        if ($validator->fails()) {
            $this->throwJsonValidationException($validator->errors()->toArray());
        }

        return $input;
    }

    /**
     * Keep API validation failures JSON even when a client omits Accept: application/json.
     *
     * @param  array<string, array<int, string>>  $errors
     */
    private function throwJsonValidationException(array $errors): never
    {
        throw new HttpResponseException(response()->json([
            'message' => 'The given data was invalid.',
            'errors' => $errors,
        ], 422));
    }

    private function upstreamError(RequestException $exception, string $operation, ?string $merchantOrderId): JsonResponse
    {
        $correlationId = $exception->response->header('X-Correlation-Id');

        Log::channel('kount')->error('Kount Payments Fraud request failed.', [
            'operation' => $operation,
            'merchantOrderId' => $merchantOrderId,
            'status' => $exception->response->status(),
            'correlationId' => $correlationId,
        ]);

        return response()->json(array_filter([
            'error' => 'Kount Payments Fraud request failed.',
            'correlationId' => $correlationId,
        ]), 502);
    }

    private function connectionError(ConnectionException $exception, string $operation, ?string $merchantOrderId): JsonResponse
    {
        Log::channel('kount')->error('Could not connect to Kount Payments Fraud.', [
            'operation' => $operation,
            'merchantOrderId' => $merchantOrderId,
            'exception' => $exception->getMessage(),
        ]);

        return response()->json(['error' => 'Kount Payments Fraud is unavailable.'], 503);
    }
}
