require 'httparty'
require 'jwt'
require 'retriable'

class TokenManager
  AUTH_SERVER_URL = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token"
  REFRESH_TIME_BUFFER = 2 * 60 # Refresh 2 minutes before expiry
  API_KEY = ENV['API_KEY']

  @access_token = nil

  class << self
    attr_accessor :access_token

    def fetch_or_refresh_token
      Rails.logger.info "🔍 Checking if JWT token needs refresh..."
    
      return if @access_token && valid_token?(@access_token)
    
      Rails.logger.info "🚀 Fetching new JWT token from Kount..."
    
      # Use Retriable to retry indefinitely every 10 seconds
      Retriable.retriable(
        on: [HTTParty::Error, Net::ReadTimeout, Net::OpenTimeout, StandardError], # Errors to retry
        base_interval: 10, # Wait 10 seconds between retries
        max_elapsed_time: nil # Retry indefinitely
      ) do
        response = HTTParty.post(AUTH_SERVER_URL,
          headers: {
            "Authorization" => "Basic #{API_KEY}",
            "Content-Type" => "application/x-www-form-urlencoded"
          },
          body: { grant_type: "client_credentials", scope: "k1_integration_api" }
        )
    
        if response.success?
          token = response.parsed_response["access_token"]
          @access_token = token
    
          # Calculate next refresh time
          exp_time = JWT.decode(token, nil, false)[0]["exp"]
          refresh_time = exp_time - REFRESH_TIME_BUFFER
    
          Rails.logger.info "✅ New JWT token set, expires at: #{Time.at(exp_time)}"
          Rails.logger.info "⏳ Next refresh scheduled for: #{Time.at(refresh_time)}"
    
          # Schedule the next refresh
          schedule_refresh_at(refresh_time)
        else
          Rails.logger.error "❌ Failed to fetch token: #{response.body}"
          raise "JWT token refresh failed!"
        end
      end
    end
    
    def valid_token?(token)
      begin
        decoded = JWT.decode(token, nil, false)[0]
        expiration_time = decoded["exp"] - REFRESH_TIME_BUFFER
        expiration_time > Time.now.to_i
      rescue JWT::DecodeError
        false
      end
    end

    def schedule_refresh_at(refresh_time)
      wait_time = refresh_time - Time.now.to_i
      wait_time = 10 if wait_time <= 0 # Avoid negative sleep time

      Rails.logger.info "🕒 Scheduling token refresh in #{wait_time} seconds..."

      Thread.new do
        sleep wait_time
        Rails.logger.info "🔄 Refreshing token now..."
        fetch_or_refresh_token
      end
    end
  end
end