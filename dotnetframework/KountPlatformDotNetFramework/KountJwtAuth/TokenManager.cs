using System;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using System.Collections.Generic;


namespace KountJwtAuth
{
    public class TokenManager
    {
        private static readonly Lazy<TokenManager> instance = new Lazy<TokenManager>(() => new TokenManager());
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
        private readonly SemaphoreSlim _refreshLock = new SemaphoreSlim(1, 1);
        private readonly HttpClient _httpClient;
        private readonly string _authUrl;
        private readonly string _apiKey;
        private readonly TimeSpan _refreshBuffer = TimeSpan.FromMinutes(2);
        private Timer _autoRefreshTimer = null;
        
        public Timer AutoRefreshTimer { get => _autoRefreshTimer; set => _autoRefreshTimer = value; }

        public TokenService(HttpClient httpClient)
        {
            _httpClient = httpClient;
            _authUrl = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token";
            _apiKey = Environment.GetEnvironmentVariable("KOUNT_API_KEY") ?? throw new ArgumentNullException("KOUNT_API_KEY");
        }

        public async Task<string> GetValidTokenAsync()
        {
            var manager = TokenManager.Instance;
            if (string.IsNullOrEmpty(manager.GetAccessToken()) || manager.IsTokenNearExpiry(_refreshBuffer))
            {
                await RefreshTokenAsync();
            }

            if (AutoRefreshTimer == null)
            {
                AutoRefreshTimer = new Timer(async _ =>
                {
                    await AutoRefreshCallback();
                }, null, TimeSpan.FromSeconds(30), TimeSpan.FromSeconds(30));
            }

            return manager.GetAccessToken();
        }

        private async Task RefreshTokenAsync()
        {
            await _refreshLock.WaitAsync();
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Post, _authUrl);
                request.Headers.Authorization = new AuthenticationHeaderValue("Basic", _apiKey);
                request.Content = new FormUrlEncodedContent(new[]
                {
                    new KeyValuePair<string, string>("grant_type", "client_credentials"),
                    new KeyValuePair<string, string>("scope", "k1_integration_api")
                });
                request.Content.Headers.ContentType = new MediaTypeHeaderValue("application/x-www-form-urlencoded");
                request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

                var response = await _httpClient.SendAsync(request);
                response.EnsureSuccessStatusCode();

                var json = await response.Content.ReadAsStringAsync();
                var token = JsonConvert.DeserializeObject<TokenResponse>(json);
                if (token?.AccessToken == null || token.ExpiresIn <= 0)
                {
                    throw new Exception("Invalid token response from Kount API");
                }

                var expiration = DateTime.UtcNow.AddSeconds(token.ExpiresIn);
                TokenManager.Instance.SetAccessToken(token.AccessToken, expiration);
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
                    await RefreshTokenAsync();
                }
            }
            catch
            {
                // Suppress background exceptions
            }
        }
    }

    public class TokenResponse
    {
        [JsonProperty("access_token")]
        public string AccessToken { get; set; } = string.Empty;

        [JsonProperty("expires_in")]
        public int ExpiresIn { get; set; }

        [JsonProperty("token_type")]
        public string TokenType { get; set; } = string.Empty;

        [JsonProperty("scope")]
        public string Scope { get; set; } = string.Empty;
    }
}