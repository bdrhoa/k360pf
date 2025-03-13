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
  #AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
  KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true"
  #REFRESH_TIME_BUFFER = 2 * 60 # Refresh 2 minutes before expiry
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
    Rails.logger.info "Using access token: #{TokenManager.access_token}..."
  
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
  def build_payload(data)
    {
      "merchantOrderId" => data["order_id"],
      "channel" => data["channel"],
      "deviceSessionId" => data["device_session_id"],
      "creationDateTime" => data["creation_datetime"],
      "userIp" => data["user_ip"],
      "account" => data["account"],
      "items" => data["items"],
      "fulfillment" => data["fulfillment"],
      "transactions" => data["transactions"],
      "customFields" => data["custom_fields"]
    }.compact
  end
end