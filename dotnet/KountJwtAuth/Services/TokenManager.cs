// TokenManager.cs
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using System.Threading;

namespace KountJwtAuth.Services
{
    public class TokenManager
    {
        private static readonly Lazy<TokenManager> instance = new(() => new TokenManager());

        private string _accessToken = string.Empty;
        private DateTime _expiration;

        public static TokenManager Instance => instance.Value;

        private TokenManager() { }

        public string GetAccessToken() => _accessToken;

        public void SetAccessToken(string token, DateTime expiration)
        {
            _accessToken = token;
            _expiration = expiration;
        }

        public bool IsTokenNearExpiry(TimeSpan buffer)
        {
            return DateTime.UtcNow.Add(buffer) >= _expiration;
        }
    }

    public class TokenService
    {
        private readonly SemaphoreSlim _refreshLock = new(1, 1);
        private readonly HttpClient _httpClient;
        private readonly IConfiguration _configuration;
        private readonly ILogger<TokenService> _logger;
        private readonly string _authUrl;
        private readonly string _apiKey;
        private readonly TimeSpan _refreshBuffer = TimeSpan.FromMinutes(2);
        private Timer? _autoRefreshTimer;

        public TokenService(HttpClient httpClient, IConfiguration configuration, ILogger<TokenService> logger)
        {
            _httpClient = httpClient;
            _configuration = configuration;
            _logger = logger;
            _authUrl = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token";
            _apiKey = configuration["Kount:ApiKey"] ?? throw new ArgumentNullException("Kount:ApiKey");
        }

        /// <summary>
        /// Retrieves a valid access token, refreshing it if near expiry.
        /// HTTP requests are automatically retried using Polly policy defined in Program.cs.
        /// </summary>
        public async Task<string> GetValidTokenAsync()
        {
            var manager = TokenManager.Instance;
            if (string.IsNullOrEmpty(manager.GetAccessToken()) || manager.IsTokenNearExpiry(_refreshBuffer))
            {
                await RefreshTokenAsync();
            }
            
            if (_autoRefreshTimer == null)
            {
                _autoRefreshTimer = new Timer(async _ =>
                {
                    await AutoRefreshCallback();
                }, null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
            }

            return manager.GetAccessToken();
        }

        /// <summary>
        /// Fetches a new token from the Kount authentication server.
        /// Automatically retried using the Polly retry policy configured for HttpClient.
        /// </summary>
        private async Task RefreshTokenAsync()
        {
            await _refreshLock.WaitAsync();
            try
            {
                _logger.LogInformation("Refreshing Kount access token...");
                var request = new HttpRequestMessage(HttpMethod.Post, _authUrl);
                request.Headers.Authorization = new AuthenticationHeaderValue("Basic", _apiKey);
                request.Content = new FormUrlEncodedContent(new[]
                {
                    new KeyValuePair<string, string>("grant_type", "client_credentials"),
                    new KeyValuePair<string, string>("scope", "k1_integration_api")
                });
                request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/x-www-form-urlencoded");
                
                request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
                
                var response = await _httpClient.SendAsync(request); // Retry handled by Polly
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                _logger.LogInformation("Received token response: {Json}", json);
                var token = JsonSerializer.Deserialize<TokenResponse>(json);
                _logger.LogInformation("Deserialized token response: {Token}", token);
                if (token?.AccessToken == null || token.ExpiresIn <= 0)
                {
                    throw new Exception("Invalid token response from Kount API");
                }

                var expiration = DateTime.UtcNow.AddSeconds(token.ExpiresIn);
                TokenManager.Instance.SetAccessToken(token.AccessToken, expiration);
                _logger.LogInformation("Token successfully refreshed, expires at {Expiration}", expiration);
            }
            finally
            {
                _refreshLock.Release();
            }
        }

        private async Task AutoRefreshCallback()
        {
            try
            {
                var manager = TokenManager.Instance;
                if (manager.IsTokenNearExpiry(_refreshBuffer))
                {
                    _logger.LogInformation("Auto-refreshing Kount access token...");
                    await RefreshTokenAsync();
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to auto-refresh Kount access token.");
            }
        }
    }

    public class TokenResponse
    {
        [JsonPropertyName("access_token")]
        public string AccessToken { get; set; } = string.Empty;

        [JsonPropertyName("expires_in")]
        public int ExpiresIn { get; set; }

        [JsonPropertyName("token_type")]
        public string TokenType { get; set; } = string.Empty;

        [JsonPropertyName("scope")]
        public string Scope { get; set; } = string.Empty;
    }
}
