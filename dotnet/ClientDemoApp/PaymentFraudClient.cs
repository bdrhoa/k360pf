using System.Globalization;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace ClientDemoApp;

internal class PaymentFraudClient
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly TokenService _tokenService;
    private readonly TokenManager _tokenManager;
    private readonly ILogger<PaymentFraudClient> _logger;

    public PaymentFraudClient(
        HttpClient httpClient,
        IConfiguration configuration,
        TokenService tokenService,
        TokenManager tokenManager,
        ILogger<PaymentFraudClient> logger)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _tokenService = tokenService;
        _tokenManager = tokenManager;
        _logger = logger;
    }

    public async Task<Dictionary<string, object>?> EvaluateDemoOrderAsync()
    {
        await _tokenService.GetValidTokenAsync();
        var token = _tokenManager.GetAccessToken();
        if (string.IsNullOrWhiteSpace(token))
        {
            throw new InvalidOperationException("TokenManager did not return a JWT.");
        }

        var apiBaseUrl = _configuration["KOUNT_API_BASE_URL"] ?? "https://api-sandbox.kount.com";
        var payload = BuildDemoOrderPayload();

        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"{apiBaseUrl.TrimEnd('/')}/commerce/v2/orders?riskInquiry=true")
        {
            Content = JsonContent.Create(payload)
        };
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);

        _logger.LogInformation(
            "Posting Payment Fraud order evaluation to Kount. apiBaseUrl={ApiBaseUrl}, merchantOrderId={MerchantOrderId}",
            apiBaseUrl,
            payload["merchantOrderId"]);

        using var response = await _httpClient.SendAsync(request);
        var responseBody = await response.Content.ReadAsStringAsync();
        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError(
                "Kount Payment Fraud order evaluation failed. status={StatusCode}, responseBody={ResponseBody}",
                response.StatusCode,
                responseBody);
            response.EnsureSuccessStatusCode();
        }

        _logger.LogInformation(
            "Kount Payment Fraud order evaluation succeeded. responseBody={ResponseBody}",
            responseBody);
        return JsonSerializer.Deserialize<Dictionary<string, object>>(responseBody);
    }

    private Dictionary<string, object> BuildDemoOrderPayload()
    {
        var now = DateTimeOffset.UtcNow.ToString("O", CultureInfo.InvariantCulture);
        var channel = _configuration["KOUNT_CHANNEL"];
        if (string.IsNullOrWhiteSpace(channel))
        {
            channel = "DEFAULT";
        }

        return new Dictionary<string, object>
        {
            ["merchantOrderId"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds().ToString(CultureInfo.InvariantCulture),
            ["channel"] = channel,
            ["deviceSessionId"] = Guid.NewGuid().ToString("N"),
            ["creationDateTime"] = now,
            ["userIp"] = "641b:e60b:16b0:f329:db24:9b7a:48bc:72e3",
            ["account"] = new Dictionary<string, object>
            {
                ["id"] = "554",
                ["type"] = "circuit",
                ["creationDateTime"] = now,
                ["username"] = "Dexter43",
                ["accountIsActive"] = false
            },
            ["items"] = new[]
            {
                new Dictionary<string, object>
                {
                    ["price"] = 544,
                    ["description"] = "Crepusculum toties pectus aggredior harum adulatio cado.",
                    ["name"] = "Sleek Granite Towels",
                    ["quantity"] = 9,
                    ["category"] = "Health",
                    ["subCategory"] = "monitor",
                    ["isDigital"] = false,
                    ["sku"] = "914",
                    ["upc"] = "304",
                    ["brand"] = "driver",
                    ["url"] = "https://prudent-barge.biz/",
                    ["imageUrl"] = "https://picsum.photos/seed/sgMI4Cvo/1972/1881",
                    ["physicalAttributes"] = new Dictionary<string, object>
                    {
                        ["color"] = "white",
                        ["size"] = "bandwidth",
                        ["weight"] = "713",
                        ["height"] = "109",
                        ["width"] = "716",
                        ["depth"] = "964"
                    },
                    ["descriptors"] = new[] { "bandwidth", "sensor" },
                    ["id"] = "504",
                    ["isService"] = true
                }
            },
            ["fulfillment"] = new[]
            {
                new Dictionary<string, object>
                {
                    ["type"] = "SHIPPED",
                    ["shipping"] = new Dictionary<string, object>
                    {
                        ["amount"] = 366,
                        ["provider"] = "Kessler - Labadie",
                        ["trackingNumber"] = "92bf50dd-c632-42ce-84aa-4a111db19c0d",
                        ["method"] = "STANDARD"
                    },
                    ["recipientPerson"] = new Dictionary<string, object>
                    {
                        ["name"] = new Dictionary<string, object>
                        {
                            ["first"] = "Albert",
                            ["preferred"] = "Karl",
                            ["family"] = "Schimmel",
                            ["middle"] = "microchip",
                            ["prefix"] = "Miss",
                            ["suffix"] = "III"
                        },
                        ["phoneNumber"] = "(705) 961-8982 x8669",
                        ["emailAddress"] = "Waino.Murray@yahoo.com",
                        ["address"] = BuildDemoAddress(),
                        ["dateOfBirth"] = "2025-04-11T19:13:55.310Z"
                    },
                    ["items"] = new[]
                    {
                        new Dictionary<string, object> { ["id"] = "26", ["quantity"] = 58330778 }
                    },
                    ["status"] = "FULFILLED",
                    ["accessUrl"] = "https://insidious-lay.org/",
                    ["store"] = new Dictionary<string, object>
                    {
                        ["id"] = "836",
                        ["name"] = "Bartoletti - Bartoletti",
                        ["address"] = BuildDemoAddress()
                    },
                    ["merchantFulfillmentId"] = "26ab50eb-81d7-4dd9-a132-9b4c3e183fb2",
                    ["digitalDownloaded"] = true,
                    ["downloadDeviceIp"] = "6c38:b69b:b691:6da1:8434:fca6:0bc4:ba0e"
                }
            },
            ["transactions"] = new[]
            {
                new Dictionary<string, object>
                {
                    ["processor"] = "monitor",
                    ["processorMerchantId"] = "PK40YMKA5004800740030268",
                    ["payment"] = new Dictionary<string, object>
                    {
                        ["type"] = "CARD",
                        ["paymentToken"] = "411111WMS5YA6FUZA1KC",
                        ["bin"] = "411111",
                        ["last4"] = "1111"
                    },
                    ["subtotal"] = 4896,
                    ["orderTotal"] = 4896,
                    ["currency"] = "USD",
                    ["tax"] = new Dictionary<string, object>
                    {
                        ["isTaxable"] = true,
                        ["taxableCountryCode"] = "US",
                        ["taxAmount"] = 29376
                    },
                    ["billedPerson"] = new Dictionary<string, object>
                    {
                        ["name"] = new Dictionary<string, object>
                        {
                            ["first"] = "Branson",
                            ["preferred"] = "Albert",
                            ["family"] = "Bergstrom",
                            ["middle"] = "interface",
                            ["prefix"] = "Mr.",
                            ["suffix"] = "IV"
                        },
                        ["phoneNumber"] = "797.718.8113 x6706",
                        ["emailAddress"] = "Monroe_Lebsack@yahoo.com",
                        ["address"] = BuildDemoAddress(),
                        ["dateOfBirth"] = "2025-06-22T05:21:42.092Z"
                    },
                    ["merchantTransactionId"] = Guid.NewGuid().ToString(),
                    ["items"] = new[]
                    {
                        new Dictionary<string, object> { ["id"] = "60", ["quantity"] = 79866928 }
                    }
                }
            },
            ["promotions"] = new[]
            {
                new Dictionary<string, object>
                {
                    ["id"] = Guid.NewGuid().ToString(),
                    ["description"] = "Tolero concido carus aeger eaque deripio capitulus.",
                    ["status"] = "capacitor",
                    ["statusReason"] = "protocol",
                    ["discount"] = new Dictionary<string, object>
                    {
                        ["percentage"] = "633",
                        ["amount"] = 472,
                        ["currency"] = "LYD"
                    },
                    ["credit"] = new Dictionary<string, object>
                    {
                        ["creditType"] = "application",
                        ["amount"] = 215,
                        ["currency"] = "BDT"
                    }
                }
            },
            ["loyalty"] = new Dictionary<string, object>
            {
                ["id"] = Guid.NewGuid().ToString(),
                ["description"] = "Tolero balbus victoria desidero aspernatur sui torqueo templum tot vae.",
                ["credit"] = new Dictionary<string, object>
                {
                    ["creditType"] = "matrix",
                    ["amount"] = 931,
                    ["currency"] = "QAR"
                }
            },
            ["customFields"] = new Dictionary<string, object>
            {
                ["keyNumber"] = "67",
                ["keyBoolean"] = false,
                ["keyString"] = "sensor",
                ["keyDate"] = now
            }
        };
    }

    private static Dictionary<string, object> BuildDemoAddress()
    {
        return new Dictionary<string, object>
        {
            ["line1"] = "5700 Yonge St, Suite 1700",
            ["city"] = "Toronto",
            ["region"] = "ON",
            ["countryCode"] = "CA",
            ["postalCode"] = "M2M 4K2"
        };
    }
}
