using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace ClientDemoApp;

internal class LoginV2Client
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly TokenService _tokenService;
    private readonly TokenManager _tokenManager;
    private readonly ILogger<LoginV2Client> _logger;

    public LoginV2Client(
        HttpClient httpClient,
        IConfiguration configuration,
        TokenService tokenService,
        TokenManager tokenManager,
        ILogger<LoginV2Client> logger)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _tokenService = tokenService;
        _tokenManager = tokenManager;
        _logger = logger;
    }

    public async Task<Dictionary<string, object>?> SubmitDemoLoginAsync()
    {
        await _tokenService.GetValidTokenAsync();
        var token = _tokenManager.GetAccessToken();
        if (string.IsNullOrWhiteSpace(token))
        {
            throw new InvalidOperationException("TokenManager did not return a JWT.");
        }

        var apiBaseUrl = _configuration["KOUNT_API_BASE_URL"] ?? "https://api-sandbox.kount.com";
        var payload = BuildDemoPayload();

        using var request = new HttpRequestMessage(HttpMethod.Post, $"{apiBaseUrl.TrimEnd('/')}/login/v2")
        {
            Content = JsonContent.Create(payload)
        };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        _logger.LogInformation(
            "Posting Login V2 inquiry to Kount. apiBaseUrl={ApiBaseUrl}, inquiryId={InquiryId}",
            apiBaseUrl,
            payload["inquiryId"]);

        using var response = await _httpClient.SendAsync(request);
        var responseBody = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError(
                "Kount Login V2 post failed. status={StatusCode}, responseBody={ResponseBody}",
                response.StatusCode,
                responseBody);
            response.EnsureSuccessStatusCode();
        }

        var correlationId = response.Headers.TryGetValues("x-correlation-id", out var values)
            ? values.FirstOrDefault()
            : null;

        _logger.LogInformation(
            "Kount Login V2 post succeeded. correlationId={CorrelationId}, responseBody={ResponseBody}",
            correlationId,
            responseBody);
        return JsonSerializer.Deserialize<Dictionary<string, object>>(responseBody);
    }

    private Dictionary<string, object> BuildDemoPayload()
    {
        var channel = _configuration["KOUNT_CHANNEL"];
        if (string.IsNullOrWhiteSpace(channel))
        {
            channel = "DEFAULT";
        }

        return new Dictionary<string, object>
        {
            ["inquiryId"] = Guid.NewGuid().ToString("N"),
            ["channel"] = channel,
            ["deviceSessionId"] = Guid.NewGuid().ToString("N"),
            ["userIp"] = "192.168.0.1",
            ["loginUrl"] = "https://www.example.com/login",
            ["person"] = new Dictionary<string, object>
            {
                ["name"] = new Dictionary<string, object>
                {
                    ["first"] = "John",
                    ["last"] = "Doe",
                    ["preferred"] = "Johnny"
                },
                ["emailAddress"] = "john.doe@example.com",
                ["phoneNumber"] = "+12081234567",
                ["addresses"] = new[]
                {
                    new Dictionary<string, object>
                    {
                        ["line1"] = "5813-5849 Quail Meadows Dr",
                        ["line2"] = "",
                        ["city"] = "Poplar Bluff",
                        ["region"] = "CO",
                        ["postalCode"] = "63901-0000",
                        ["countryCode"] = "USA",
                        ["addressType"] = "BILLING"
                    }
                }
            },
            ["account"] = new Dictionary<string, object>
            {
                ["id"] = "meoyyd8za8jdmwfm",
                ["type"] = "VIP",
                ["creationDateTime"] = "2024-01-01T12:12:12.000Z",
                ["username"] = "meoyyd8za8jdmwfm",
                ["userPassword"] = "hashedpassword",
                ["accountIsActive"] = true
            },
            ["strategy"] = new Dictionary<string, object>
            {
                ["mfaTemplateName"] = "default",
                ["mfaTemplateValues"] = new Dictionary<string, object>
                {
                    ["firstName"] = "John",
                    ["accountType"] = "VIP"
                }
            },
            ["customFields"] = new Dictionary<string, object>
            {
                ["exampleBoolean"] = true,
                ["exampleNumber"] = 42,
                ["exampleString"] = ".NET Login demo"
            }
        };
    }
}
