using KountWebhookSignatureVerifier;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using System;
using WebhookSignatureVerifier;
using WebhookSignatureVerifier.Services;

namespace KountWebhookSignatureVerifier.Tests
{
    [TestClass]
    public class SignatureVerifierTests
    {
        [TestMethod]
        public void VerifySignature_WithValidSignature_ReturnsTrue()
        {
            // Arrange
            var logger = new FakeLogger<SignatureVerifier>();
            var verifier = new SignatureVerifier(logger);

            //var payload = System.Text.Encoding.UTF8.GetBytes("test-payload");
            //var timestamp = DateTime.UtcNow.ToString("o");
            string rawJson = "{\"id\":\"321bc10b-b49d-4b75-8caf-07fd11cc4ad2\",\"eventType\":\"Order.StatusChange\",\"apiVersion\":\"v1\",\"clientId\":\"928737379799093\",\"kountOrderId\":\"0XWFM3QPGN5G1F7C\",\"merchantOrderId\":\"1754456650015\",\"orderCreationDate\":\"2025-07-01T00:57:29.849Z\",\"eventDate\":\"2025-07-01T00:58:20Z\",\"fieldName\":\"status\",\"oldValue\":\"REVIEW\",\"newValue\":\"DECLINE\",\"channel\":\"WEBHTEST\"}";
            var payload = System.Text.Encoding.UTF8.GetBytes(rawJson);
            //var timestamp = "2025-07-01T00:58:21Z";
            var timestamp = "2025-07-01T00:58:21.0000000Z";
            var fixedTime = DateTime.Parse(timestamp).ToUniversalTime();

            // You must set KOUNT_PUBLIC_KEY environment variable to your real key before running this test
            // var signature = GenerateValidSignature(payload, timestamp); // Assume you have a method for that
            var signature = "Qth86BE0OTQ/AU/R9o121MaE6lYJAWQwQzfcLGfCdi4kn7VabAptF/j29f0dUP2Sgk2eqcK21hPMsr5bptEZLQNoMbX/19N/9vePJBkbTwwHTV2QSOzOfAfLsZFYbBQFYrEphAwsmipFHsIO3d0+jjJcF3Kf+zzBAi5CZ7IpoKLttjmf9xaDgfYHcDcvx3jbkuEaOyshwnedLEx5SD6Uk1WW2WIf/gpQdK2+jBjgryn1L7LNytyFt7PmC+gHWqZSgpAaOhymy3GoL5utzvYphGmkgLvA1CQB0RojHV69DnQ2DQ47pfIaUdLPeyGw8mfB26+ZMScf8LyMjt4yhPDg3yfc8mNAcBLpXzaBb3RRdkRgXvq2R0/D/19dqRhl0JuAB9IWmM/eF44uPBJ253hYzgDe5uULAisoPr2ual4JToJu3NDzjY3sU0RPEFzNyY46JzjEabtrIBu+HfEN4T+QgHccfutHf9QZb6YHUkax5GqLyerZBdOyVnCqDYnqAHfnOePAKEi2DYwPpqQPJfNu3vI17M+Y3liFonaE+J7Upt9xtFsI1vrpr31eok/xZjLOsIv0AdkuLb7SWpt6JmG+UYP7ijNp6eLr8kbHpXoQbVlBcfggnwrFXvIjcR9/bYZ0ukUkQcU/hnSZDzA83Xr692CEb4+VlAIEqcDBsNA5AkU="; // Placeholder for the actual signature
            var result = verifier.VerifySignature(signature, timestamp, payload, fixedTime);
            // Assert
            Assert.IsTrue(result);
        }
    }
}