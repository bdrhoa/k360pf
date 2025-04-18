// TokenManager.cs
using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

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
        private readonly HttpClient _httpClient;
        private readonly IConfiguration _configuration;
        private readonly ILogger<TokenService> _logger;
        private readonly string _authUrl;
        private readonly string _apiKey;
        private readonly TimeSpan _refreshBuffer = TimeSpan.FromMinutes(2);

        public TokenService(HttpClient httpClient, IConfiguration configuration, ILogger<TokenService> logger)
        {
            _httpClient = httpClient;
            _configuration = configuration;
            _logger = logger;
            _authUrl = configuration["Kount:AuthUrl"] ?? throw new ArgumentNullException("Kount:AuthUrl");
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
            return manager.GetAccessToken();
        }

        /// <summary>
        /// Fetches a new token from the Kount authentication server.
        /// Automatically retried using the Polly retry policy configured for HttpClient.
        /// </summary>
        private async Task RefreshTokenAsync()
        {
            _logger.LogInformation("Refreshing Kount access token...");
            var request = new HttpRequestMessage(HttpMethod.Post, _authUrl);
            request.Headers.Authorization = new AuthenticationHeaderValue("Basic", _apiKey);
            request.Content = new StringContent("grant_type=client_credentials", Encoding.UTF8, "application/x-www-form-urlencoded");

            var response = await _httpClient.SendAsync(request); // Retry handled by Polly
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var token = JsonSerializer.Deserialize<TokenResponse>(json);

            if (token?.AccessToken == null || token.ExpiresIn <= 0)
            {
                throw new Exception("Invalid token response from Kount API");
            }

            var expiration = DateTime.UtcNow.AddSeconds(token.ExpiresIn);
            TokenManager.Instance.SetAccessToken(token.AccessToken, expiration);
            _logger.LogInformation("Token successfully refreshed, expires at {Expiration}", expiration);
        }
    }

    public class TokenResponse
    {
    public string AccessToken { get; set; } = string.Empty;
        public int ExpiresIn { get; set; }
    public string TokenType { get; set; } = string.Empty;
    public string Scope { get; set; } = string.Empty;
    }
}
