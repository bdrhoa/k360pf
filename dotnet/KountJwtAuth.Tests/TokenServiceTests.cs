using System;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using KountJwtAuth.Services;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using Moq.Protected;
using Xunit;

namespace KountJwtAuth.Tests
{
    public class TokenServiceTests
    {
        [Fact]
        public async Task GetValidTokenAsync_RefreshesAndReturnsToken()
        {
            // Arrange
            var tokenJson = "{ \"access_token\": \"mocktoken\", \"expires_in\": 3600 }";
            var handlerMock = new Mock<HttpMessageHandler>();
            handlerMock
                .Protected()
                .Setup<Task<HttpResponseMessage>>(
                    "SendAsync",
                    ItExpr.IsAny<HttpRequestMessage>(),
                    ItExpr.IsAny<CancellationToken>())
                .ReturnsAsync(new HttpResponseMessage
                {
                    StatusCode = HttpStatusCode.OK,
                    Content = new StringContent(tokenJson)
                });

            var httpClient = new HttpClient(handlerMock.Object);

            var config = new ConfigurationBuilder()
                .AddInMemoryCollection((IEnumerable<KeyValuePair<string, string?>>)new[]
                {
                    new KeyValuePair<string, string?>("Kount:AuthUrl", "https://mock.token.url"),
                    new KeyValuePair<string, string?>("Kount:ApiKey", "mockApiKey")
                })
                .Build();

            var loggerMock = new Mock<ILogger<TokenService>>();
            var service = new TokenService(httpClient, config, loggerMock.Object);

            // Act
            var token = await service.GetValidTokenAsync();

            // Assert
            Assert.Equal("mocktoken", token);
        }
    }
}