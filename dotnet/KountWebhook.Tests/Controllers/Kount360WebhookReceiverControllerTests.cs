using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using KountJwtAuth.Services;
using KountWebhook.Controllers;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;

namespace KountWebhook.Tests.Controllers
{
    public class Kount360WebhookReceiverControllerTests
    {
        private readonly Mock<ILogger<Kount360WebhookReceiverController>> _mockLogger;
        private readonly Mock<ISignatureVerifier> _mockVerifier;

        public Kount360WebhookReceiverControllerTests()
        {
            _mockLogger = new Mock<ILogger<Kount360WebhookReceiverController>>();
            _mockVerifier = new Mock<ISignatureVerifier>();
        }

        private Kount360WebhookReceiverController CreateController(string body, string timestamp, string signature)
        {
            var controller = new Kount360WebhookReceiverController(_mockLogger.Object, _mockVerifier.Object);
            var context = new DefaultHttpContext();
            context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
            context.Request.Headers["X-Event-Timestamp"] = timestamp;
            context.Request.Headers["X-Event-Signature"] = signature;
            controller.ControllerContext = new ControllerContext { HttpContext = context };
            return controller;
        }

        [Fact]
        public async Task Post_ReturnsBadRequest_WhenMissingTimestamp()
        {
            var controller = CreateController("{}", null!, "signature");
            var result = await controller.Post();
            Assert.IsType<BadRequestObjectResult>(result);
        }

        [Fact]
        public async Task Post_ReturnsBadRequest_WhenMissingSignature()
        {
            var controller = CreateController("{}", "timestamp", null!);
            var result = await controller.Post();
            Assert.IsType<BadRequestObjectResult>(result);
        }

        [Fact]
        public async Task Post_ReturnsServerError_WhenBodyIsEmpty()
        {
            var controller = CreateController("", "timestamp", "signature");
            var result = await controller.Post();
            var objectResult = Assert.IsType<ObjectResult>(result);
            Assert.Equal(500, objectResult.StatusCode);
        }

        [Fact]
        public async Task Post_ReturnsBadRequest_WhenSignatureVerificationFails()
        {
            _mockVerifier.Setup(v => v.VerifySignature(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<byte[]>(), null))
                         .Throws(new ArgumentException("Invalid signature"));
            var controller = CreateController("{}", "timestamp", "signature");
            var result = await controller.Post();
            Assert.IsType<BadRequestObjectResult>(result);
        }

        [Fact]
        public async Task Post_ReturnsServerError_WhenVerifierThrowsInvalidOperationException()
        {
            _mockVerifier.Setup(v => v.VerifySignature(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<byte[]>(), null))
                         .Throws(new InvalidOperationException("Key error"));
            var controller = CreateController("{}", "timestamp", "signature");
            var result = await controller.Post();
            var objectResult = Assert.IsType<ObjectResult>(result);
            Assert.Equal(500, objectResult.StatusCode);
        }

        [Fact]
        public async Task Post_ReturnsBadRequest_WhenPayloadIsInvalidJson()
        {
            var controller = CreateController("not-json", "timestamp", "signature");
            _mockVerifier.Setup(v => v.VerifySignature(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<byte[]>(), null)).Returns(true);
            var result = await controller.Post();
            Assert.IsType<BadRequestObjectResult>(result);
        }

        [Theory]
        [InlineData("APPROVE")]
        [InlineData("DECLINE")]
        [InlineData("SOMETHING_ELSE")]
        public async Task Post_HandlesValidJsonPayloads(string newValue)
        {
            var json = $"{{\"newValue\":\"{newValue}\"}}";
            var controller = CreateController(json, "timestamp", "signature");
            _mockVerifier.Setup(v => v.VerifySignature(It.IsAny<string>(), It.IsAny<string>(), It.IsAny<byte[]>(), null)).Returns(true);
            var result = await controller.Post();
            var okResult = Assert.IsType<OkObjectResult>(result);
            var response = Assert.IsType<WebhookResponse>(okResult.Value);
            Assert.Equal("ok", response.Status);
        }
    }
}