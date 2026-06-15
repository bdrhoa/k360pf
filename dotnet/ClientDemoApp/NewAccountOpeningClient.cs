using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace ClientDemoApp;

internal class NewAccountOpeningClient
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly TokenService _tokenService;
    private readonly TokenManager _tokenManager;
    private readonly ILogger<NewAccountOpeningClient> _logger;

    public NewAccountOpeningClient(
        HttpClient httpClient,
        IConfiguration configuration,
        TokenService tokenService,
        TokenManager tokenManager,
        ILogger<NewAccountOpeningClient> logger)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _tokenService = tokenService;
        _tokenManager = tokenManager;
        _logger = logger;
    }

    public async Task<Dictionary<string, object>?> SubmitDemoInquiryAsync()
    {
        await _tokenService.GetValidTokenAsync();
        var token = _tokenManager.GetAccessToken();
        if (string.IsNullOrWhiteSpace(token))
        {
            throw new InvalidOperationException("TokenManager did not return a JWT.");
        }

        var apiBaseUrl = _configuration["KOUNT_API_BASE_URL"] ?? "https://api-sandbox.kount.com";
        var payload = BuildDemoPayload();

        using var request = new HttpRequestMessage(HttpMethod.Post, $"{apiBaseUrl.TrimEnd('/')}/newaccountopening/v2")
        {
            Content = JsonContent.Create(payload)
        };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        _logger.LogInformation(
            "Posting NAO V2 inquiry to Kount. apiBaseUrl={ApiBaseUrl}, inquiryId={InquiryId}",
            apiBaseUrl,
            payload["inquiryId"]);

        using var response = await _httpClient.SendAsync(request);
        var responseBody = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError(
                "Kount NAO V2 post failed. status={StatusCode}, responseBody={ResponseBody}",
                response.StatusCode,
                responseBody);
            response.EnsureSuccessStatusCode();
        }

        _logger.LogInformation("Kount NAO V2 post succeeded. responseBody={ResponseBody}", responseBody);
        return JsonSerializer.Deserialize<Dictionary<string, object>>(responseBody);
    }

    private Dictionary<string, object> BuildDemoPayload()
    {
        var deviceSessionId = Guid.NewGuid().ToString("N");
        var channel = _configuration["KOUNT_CHANNEL"];
        if (string.IsNullOrWhiteSpace(channel))
        {
            channel = "DEFAULT";
        }

        var payload = new Dictionary<string, object>
        {
            ["inquiryId"] = $"nao-dotnet-{Guid.NewGuid()}",
            ["channel"] = channel,
            ["deviceSessionId"] = deviceSessionId,
            ["userIp"] = "192.168.0.1",
            ["accountCreationUrl"] = "https://www.example.com/create-account",
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
                ["id"] = "11223dr44",
                ["type"] = "VIP",
                ["username"] = "meoyyd8za8jdmwfm"
            },
            ["strategy"] = new Dictionary<string, object>
            {
                ["verificationTemplateName"] = "default",
                ["verificationTemplateValues"] = new Dictionary<string, object>
                {
                    ["firstName"] = "John",
                    ["accountType"] = "VIP"
                }
            },
            ["customFields"] = new Dictionary<string, object>
            {
                ["exampleBoolean"] = true,
                ["exampleNumber"] = 42,
                ["exampleString"] = ".NET NAO demo"
            }
        };

        var clientId = _configuration["KOUNT_CLIENT_ID"];
        if (!string.IsNullOrWhiteSpace(clientId))
        {
            payload["sharedContext"] = new Dictionary<string, object>
            {
                ["sourceClientId"] = clientId,
                ["sourceDeviceSessionId"] = deviceSessionId
            };
        }

        return payload;
    }
}
