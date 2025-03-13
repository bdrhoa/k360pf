require Rails.root.join('app/services/token_manager') # Ensure TokenManager is loaded

Thread.new do
  begin
    Rails.logger.info "🔄 Initializing background token refresher..."
    TokenManager.fetch_or_refresh_token
  rescue => e
    Rails.logger.error "❌ Token refresh error: #{e.message}"
  end
end