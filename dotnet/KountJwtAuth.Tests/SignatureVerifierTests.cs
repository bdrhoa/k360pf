using System;
using System.Text;
using System.Security.Cryptography;
using Microsoft.Extensions.Logging;
using Moq;
using Xunit;
using KountJwtAuth.Services;

namespace KountJwtAuth.Tests.Services
{
    public class SignatureVerifierTests
    {
        private readonly Mock<ILogger<SignatureVerifier>> _loggerMock = new();
        private readonly SignatureVerifier _verifier;

        public SignatureVerifierTests()
        {
            _verifier = new SignatureVerifier(_loggerMock.Object, TimeSpan.FromMinutes(5));
        }

        private static (string SignatureBase64, string Timestamp, byte[] Payload, string PublicKeyBase64) GenerateValidSignature()
        {
            var payload = Encoding.UTF8.GetBytes("{ \"message\": \"Hello\" }");
            var timestamp = DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ");
            var dataToSign = Encoding.UTF8.GetBytes(timestamp).Concat(payload).ToArray();

            using var rsa = RSA.Create(2048);
            var signature = rsa.SignData(dataToSign, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
            var pubKey = rsa.ExportSubjectPublicKeyInfo();

            return (
                Convert.ToBase64String(signature),
                timestamp,
                payload,
                Convert.ToBase64String(pubKey)
            );
        }

        [Fact]
        public void VerifySignature_ValidInputs_ReturnsTrue()
        {
            var (signature, timestamp, payload, publicKeyBase64) = GenerateValidSignature();
            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", publicKeyBase64);

            var result = _verifier.VerifySignature(signature, timestamp, payload);
            Assert.True(result);
        }

        [Fact]
        public void VerifySignature_InvalidBase64Signature_Throws()
        {
            var timestamp = DateTime.UtcNow.ToString("o");
            var payload = Encoding.UTF8.GetBytes("test");
            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", Convert.ToBase64String(RSA.Create().ExportSubjectPublicKeyInfo()));

            Assert.Throws<ArgumentException>(() =>
                _verifier.VerifySignature("###INVALID###", timestamp, payload));
        }

        [Fact]
        public void VerifySignature_InvalidTimestamp_Throws()
        {
            var signature = Convert.ToBase64String(new byte[256]);
            var payload = Encoding.UTF8.GetBytes("test");
            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", Convert.ToBase64String(RSA.Create().ExportSubjectPublicKeyInfo()));

            Assert.Throws<ArgumentException>(() =>
                _verifier.VerifySignature(signature, "NOT-A-TIMESTAMP", payload));
        }

        [Fact]
        public void VerifySignature_TimestampTooOld_Throws()
        {
            var timestamp = DateTime.UtcNow.AddMinutes(-10).ToString("o");
            var payload = Encoding.UTF8.GetBytes("test");
            var digest = Encoding.UTF8.GetBytes(timestamp).Concat(payload).ToArray();

            using var rsa = RSA.Create(2048);
            var signature = rsa.SignData(digest, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
            var publicKeyBase64 = Convert.ToBase64String(rsa.ExportSubjectPublicKeyInfo());

            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", publicKeyBase64);

            Assert.Throws<ArgumentException>(() =>
                _verifier.VerifySignature(Convert.ToBase64String(signature), timestamp, payload));
        }

        [Fact]
        public void VerifySignature_TimestampTooNew_Throws()
        {
            var timestamp = DateTime.UtcNow.AddMinutes(10).ToString("o");
            var payload = Encoding.UTF8.GetBytes("test");
            var digest = Encoding.UTF8.GetBytes(timestamp).Concat(payload).ToArray();

            using var rsa = RSA.Create(2048);
            var signature = rsa.SignData(digest, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
            var publicKeyBase64 = Convert.ToBase64String(rsa.ExportSubjectPublicKeyInfo());

            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", publicKeyBase64);

            Assert.Throws<ArgumentException>(() =>
                _verifier.VerifySignature(Convert.ToBase64String(signature), timestamp, payload));
        }

        [Fact]
        public void VerifySignature_InvalidSignature_Throws()
        {
            var timestamp = DateTime.UtcNow.ToString("o");
            var payload = Encoding.UTF8.GetBytes("test");
            var badSignature = Convert.ToBase64String(new byte[256]);

            using var rsa = RSA.Create(2048);
            var publicKeyBase64 = Convert.ToBase64String(rsa.ExportSubjectPublicKeyInfo());

            Environment.SetEnvironmentVariable("KOUNT_PUBLIC_KEY", publicKeyBase64);

            Assert.Throws<ArgumentException>(() =>
                _verifier.VerifySignature(badSignature, timestamp, payload));
        }

                [Fact]
        public void VerifySignature_WithValidSignature_ReturnsTrue()
        {
            var rawJson = "{\"id\":\"321bc10b-b49d-4b75-8caf-07fd11cc4ad2\",\"eventType\":\"Order.StatusChange\",\"apiVersion\":\"v1\",\"clientId\":\"928737379799093\",\"kountOrderId\":\"0XWFM3QPGN5G1F7C\",\"merchantOrderId\":\"1754456650015\",\"orderCreationDate\":\"2025-07-01T00:57:29.849Z\",\"eventDate\":\"2025-07-01T00:58:20Z\",\"fieldName\":\"status\",\"oldValue\":\"REVIEW\",\"newValue\":\"DECLINE\",\"channel\":\"WEBHTEST\"}";
            var payload = Encoding.UTF8.GetBytes(rawJson);
            //var timestamp = "2025-07-01T00:58:21.0000000Z";
            var timestamp = "2025-07-01T00:58:21Z";
            var fixedTime = DateTime.Parse(timestamp).ToUniversalTime();

            // You must set the KOUNT_PUBLIC_KEY environment variable before running this test
            var signature = "Qth86BE0OTQ/AU/R9o121MaE6lYJAWQwQzfcLGfCdi4kn7VabAptF/j29f0dUP2Sgk2eqcK21hPMsr5bptEZLQNoMbX/19N/9vePJBkbTwwHTV2QSOzOfAfLsZFYbBQFYrEphAwsmipFHsIO3d0+jjJcF3Kf+zzBAi5CZ7IpoKLttjmf9xaDgfYHcDcvx3jbkuEaOyshwnedLEx5SD6Uk1WW2WIf/gpQdK2+jBjgryn1L7LNytyFt7PmC+gHWqZSgpAaOhymy3GoL5utzvYphGmkgLvA1CQB0RojHV69DnQ2DQ47pfIaUdLPeyGw8mfB26+ZMScf8LyMjt4yhPDg3yfc8mNAcBLpXzaBb3RRdkRgXvq2R0/D/19dqRhl0JuAB9IWmM/eF44uPBJ253hYzgDe5uULAisoPr2ual4JToJu3NDzjY3sU0RPEFzNyY46JzjEabtrIBu+HfEN4T+QgHccfutHf9QZb6YHUkax5GqLyerZBdOyVnCqDYnqAHfnOePAKEi2DYwPpqQPJfNu3vI17M+Y3liFonaE+J7Upt9xtFsI1vrpr31eok/xZjLOsIv0AdkuLb7SWpt6JmG+UYP7ijNp6eLr8kbHpXoQbVlBcfggnwrFXvIjcR9/bYZ0ukUkQcU/hnSZDzA83Xr692CEb4+VlAIEqcDBsNA5AkU=";

            var result = _verifier.VerifySignature(signature, timestamp, payload, fixedTime);
            Assert.True(result);
        }
    }
}

