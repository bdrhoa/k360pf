using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using KountJwtAuth.Services;

public class WebhookResponse
{
    public string Status { get; set; } = string.Empty;
}

namespace KountWebhook.Controllers
{
    [ApiController]
    [Route("[controller]")]
    public class Kount360WebhookReceiverController : ControllerBase
    {
        private readonly ILogger<Kount360WebhookReceiverController> _logger;
        private readonly ISignatureVerifier _signatureVerifier;

        public Kount360WebhookReceiverController(ILogger<Kount360WebhookReceiverController> logger, ISignatureVerifier signatureVerifier)
        {
            _logger = logger;
            _signatureVerifier = signatureVerifier;
        }

        [HttpPost]
        public async Task<IActionResult> Post()
        {
            var timestampHeader = Request.Headers["X-Event-Timestamp"];
            var signatureHeader = Request.Headers["X-Event-Signature"];

            if (string.IsNullOrEmpty(timestampHeader))
                return BadRequest("Missing X-Event-Timestamp header");
            if (string.IsNullOrEmpty(signatureHeader))
                return BadRequest("Missing X-Event-Signature header");

            string body;
            using (var reader = new StreamReader(Request.Body, Encoding.UTF8))
                body = await reader.ReadToEndAsync();

            if (string.IsNullOrWhiteSpace(body))
                return StatusCode(500, "Empty request body");

            try
            {
                if (string.IsNullOrEmpty(signatureHeader))
                {
                    _logger.LogError("Signature header is null or empty before verification.");
                    return BadRequest("Invalid signature header");
                }

                var payloadBytes = Encoding.UTF8.GetBytes(body);
                _signatureVerifier.VerifySignature(signatureHeader!, timestampHeader!, payloadBytes);
            }
            catch (ArgumentException ex)
            {
                _logger.LogError("Signature verification error: {Message}", ex.Message);
                return BadRequest(ex.Message);
            }
            catch (InvalidOperationException ex)
            {
                _logger.LogError("Public key error: {Message}", ex.Message);
                return StatusCode(500, ex.Message);
            }

            try
            {
                var payload = JsonSerializer.Deserialize<JsonElement>(body);
                var newValue = payload.GetProperty("newValue").GetString();

                if (newValue == "DECLINE")
                    _logger.LogInformation("Simulated order cancellation");
                else if (newValue == "APPROVE")
                    _logger.LogInformation("Simulated order processing");
                else
                    _logger.LogError("Unexpected newValue: {NewValue}", newValue);
            }
            catch (JsonException ex)
            {
                _logger.LogError("Invalid JSON payload: {Message}", ex.Message);
                return BadRequest("Invalid JSON payload");
            }

            return Ok(new WebhookResponse { Status = "ok" });
        }
    }
}