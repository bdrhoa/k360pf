# app/controllers/transactions_controller.rb

require 'json'
require 'httparty'
require 'jwt'
require 'retriable'

##
# TransactionsController handles transaction processing, interacts with the Kount API,
# and updates authorization statuses when necessary.
class TransactionsController < ApplicationController
  skip_before_action :verify_authenticity_token, only: [:process_transaction]
  before_action -> { TokenManager.fetch_or_refresh_token }, only: [:process_transaction]

  # Constants
  KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true"
  API_KEY = ENV['API_KEY']

  ##
  # Processes the transaction and interacts with the Kount API.
  def process_transaction
    Rails.logger.info "🚀 process_transaction STARTED!"

    request_data = JSON.parse(request.body.read)
    merchant_order_id = request_data["order_id"] || "UNKNOWN"

    Rails.logger.info "🔍 Incoming transaction for Order ID: #{merchant_order_id}"

    # Determine if this is a pre-authorization request
    is_pre_auth = true
    if request_data["transactions"]&.any?
      first_transaction = request_data["transactions"].first
      is_pre_auth = !first_transaction.dig("authorizationStatus", "authResult")
    end

    # Build payload
    payload = build_payload(request_data)
    Rails.logger.info "📦 Payload built for Order ID: #{merchant_order_id}"
    Rails.logger.info "📦 Payload: #{payload.to_json}"

    # Call Kount API
    response = kount_api_request(payload, is_pre_auth, merchant_order_id)

    # Extract decision and order ID
    decision = response.dig("order", "riskInquiry", "decision") || "UNKNOWN"
    kount_order_id = response.dig("order", "orderId") || "UNKNOWN"

    # If pre-auth was approved/reviewed, update authorization via PATCH
    if is_pre_auth && kount_order_id != "UNKNOWN" && merchant_order_id != "UNKNOWN" &&
       ["APPROVE", "REVIEW"].include?(decision)
      safe_patch_credit_card_authorization(kount_order_id, merchant_order_id)
    end

    render json: response
  rescue => e
    Rails.logger.error("Error processing transaction: #{e.message}")
    render json: handle_api_failure(is_pre_auth, merchant_order_id), status: 500
  end

  private

  ##
  # Calls the Kount API with retry logic.
  def kount_api_request(payload, is_pre_auth, merchant_order_id)
  
    response = nil
    Retriable.retriable(on: [HTTParty::Error, Net::ReadTimeout, Net::OpenTimeout], tries: 3, base_interval: 1, max_interval: 10) do
      response = HTTParty.post(KOUNT_API_ENDPOINT,
        headers: {
          "Authorization" => "Bearer #{TokenManager.access_token}",
          "Content-Type" => "application/json"
        },
        body: payload.to_json
      )
  
      raise "Kount API error: #{response.body}" unless response.success?
    end
  
    response.parsed_response
  rescue => e
    Rails.logger.error("Kount API call failed: #{e.message}")
    handle_api_failure(is_pre_auth, merchant_order_id)
  end
  
  ##
  # Sends a PATCH request to update credit card authorization.
  def patch_credit_card_authorization(kount_order_id, merchant_order_id)
    url = "https://api-sandbox.kount.com/commerce/v2/orders/#{kount_order_id}"
    auth_payload = simulate_credit_card_authorization(merchant_order_id)

    Retriable.retriable(on: [HTTParty::Error, Net::ReadTimeout, Net::OpenTimeout], tries: 3, base_interval: 1, max_interval: 10) do
      response = HTTParty.patch(url,
        headers: {
          "Authorization" => "Bearer #{TokenManager.access_token}",
          "Content-Type" => "application/json"
        },
        body: auth_payload.to_json
      )

      raise "Failed to patch authorization: #{response.body}" unless response.success?

      response.parsed_response
    end
  rescue => e
    Rails.logger.error("PATCH request failed: #{e.message}")
    { error: "Failed to update authorization", details: e.message }
  end

  ##
  # Handles safe execution of the PATCH request.
  def safe_patch_credit_card_authorization(kount_order_id, merchant_order_id)
    patch_credit_card_authorization(kount_order_id, merchant_order_id)
  rescue => e
    Rails.logger.error("Final failure after retries for PATCH: #{e.message}")
  end

  ##
  # Simulates a credit card authorization decision.
  def simulate_credit_card_authorization(merchant_order_id)
    {
      "order_id" => merchant_order_id,
      "transactions" => [
        {
          "authorizationStatus" => {
            "authResult" => "APPROVED",
            "verificationResponse" => {
              "cvvStatus" => "MATCH",
              "avsStatus" => "Y"
            }
          }
        }
      ]
    }
  end

  ##
  # Returns a fallback response when the Kount API is unavailable.
  def handle_api_failure(is_pre_auth, merchant_order_id)
    { "order" => { "riskInquiry" => { "decision" => "APPROVE" } } }
  end

  ##
  # Builds the payload for Kount API requests.
  def build_payload(data, patch = false)
    merchant_order_id = data["order_id"]
    raise "Missing required field: merchantOrderId" if merchant_order_id.nil? && !patch
  
    payload = {
      "merchantOrderId" => merchant_order_id,
      "channel" => data["channel"],
      "deviceSessionId" => data["device_session_id"],
      "creationDateTime" => data["creation_datetime"],
      "userIp" => data["user_ip"],
      "account" => data["account_id"] ? {
        "id" => data["account_id"],
        "type" => data["account_type"],
        "creationDateTime" => data["account_creation_datetime"],
        "username" => data["username"],
        "accountIsActive" => data["account_is_active"]
      } : nil,
      "items" => data["items"]&.map do |item|
        next unless item.is_a?(Hash)
        {
          "price" => item["price"].to_s || "0",
          "description" => item["description"],
          "name" => item["name"],
          "quantity" => item["quantity"] || 1,
          "category" => item["category"],
          "subCategory" => item["sub_category"],
          "isDigital" => item["is_digital"],
          "sku" => item["sku"],
          "upc" => item["upc"],
          "brand" => item["brand"],
          "url" => item["url"],
          "imageUrl" => item["image_url"],
          "physicalAttributes" => item.slice("color", "size", "weight", "height", "width", "depth").compact.presence,
          "descriptors" => item["descriptors"],
          "id" => item["item_id"],
          "isService" => item["is_service"]
        }.compact
      end&.compact.presence,
      "fulfillment" => data["fulfillment"]&.map do |fulfillment|
        next unless fulfillment.is_a?(Hash)
        {
          "type" => fulfillment["type"],
          "shipping" => fulfillment["shipping"]&.slice("amount", "provider", "tracking_number", "method"),
          "recipientPerson" => fulfillment["recipient"] ? {
            "name" => fulfillment["recipient"]["first"] && fulfillment["recipient"]["family"] ? {
              "first" => fulfillment["recipient"]["first"],
              "family" => fulfillment["recipient"]["family"]
            } : nil,
            "phoneNumber" => fulfillment["recipient"]["phone_number"],
            "emailAddress" => fulfillment["recipient"]["email_address"],
            "address" => fulfillment["recipient"]["address"]
          }.compact : nil,
          "merchantFulfillmentId" => fulfillment["merchant_fulfillment_id"],
          "digitalDownloaded" => fulfillment["digital_downloaded"]
        }.compact
      end&.compact.presence,
      "transactions" => data["transactions"]&.map do |transaction|
        next unless transaction.is_a?(Hash)
        {
          "processor" => transaction["processor"],
          "processorMerchantId" => transaction["processor_merchant_id"],
          "payment" => transaction["payment"]&.slice("type", "payment_token", "bin", "last4"),
          "subtotal" => transaction["subtotal"].to_s || "0",
          "orderTotal" => transaction["order_total"].to_s || "0",
          "currency" => transaction["currency"],
          "tax" => transaction["tax"]&.slice("is_taxable", "taxable_country_code", "tax_amount", "out_of_state_tax_amount"),
          "billedPerson" => transaction["billingPerson"] ? {
            "name" => transaction["billingPerson"]["name"]&.slice("first", "preferred", "family", "middle", "prefix", "suffix"),
            "phoneNumber" => transaction["billingPerson"]["phone"],
            "emailAddress" => transaction["billingPerson"]["email"],
            "address" => transaction["billingPerson"]["address"]
          }.compact : nil,
          "transactionStatus" => transaction["transaction_status"],
          "authorizationStatus" => transaction["authorizationStatus"] ? {
            "authResult" => transaction["authorizationStatus"]["authResult"],
            "dateTime" => transaction["authorizationStatus"]["dateTime"],
            "verificationResponse" => transaction["authorizationStatus"]["verificationResponse"]&.slice("cvvStatus", "avsStatus")
          }.compact : nil,
          "merchantTransactionId" => transaction["merchant_transaction_id"],
          "items" => transaction["items"]&.map { |item| item.slice("id", "quantity") if item.is_a?(Hash) }&.compact
        }.compact
      end&.compact.presence,
      "customFields" => data["custom_fields"]
    }.compact
  
    payload
  end
  
end