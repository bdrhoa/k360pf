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
            //var rawJson = "{\"id\":\"d27a75dc-6a13-40ce-83c7-d9ab963ab408\", \"eventType\":\"Order.StatusChange\", \"apiVersion\":\"v1\", \"clientId\":\"928737379799093\", \"kountOrderId\":\"V2D1MDKZXVYJXVZZ\", \"merchantOrderId\":\"d121ea2210434ffc8a90daff9cc97e76\", \"orderCreationDate\":\"2025-05-10T18:25:09.045Z\", \"eventDate\":\"2025-07-04T01:46:13Z\", \"fieldName\":\"status\", \"oldValue\":\"REVIEW\", \"newValue\":\"DECLINE\", \"channel\":\"DOTNET\"}";
            var rawJson = "{\"id\":\"d27a75dc-6a13-40ce-83c7-d9ab963ab408\", \"eventType\":\"Order.StatusChange\", \"apiVersion\":\"v1\", \"clientId\":\"928737379799093\", \"kountOrderId\":\"V2D1MDKZXVYJXVZZ\", \"merchantOrderId\":\"d121ea2210434ffc8a90daff9cc97e76\", \"orderCreationDate\":\"2025-05-10T18:25:09.045Z\", \"eventDate\":\"2025-07-04T01:46:13Z\", \"fieldName\":\"status\", \"oldValue\":\"REVIEW\", \"newValue\":\"DECLINE\", \"channel\":\"DOTNET\"}";
            var payload = Encoding.UTF8.GetBytes(rawJson);
            var timestamp = "2025-07-04T01:46:15Z";
            var signature = "Wgpzu4WT48OLo8EAaSXBhEWREv2dp0jsZiXIoo5+AHLHR36XC5TpTc1gXnD2kvyyF6LzMkpp3Zu2oye83Iui5yr6y5PWndKhsIxSGCjCu9Jeizjaw1cafoemGpejZIo+6k9IVitEc7znuZ4GjBz+SQHuVlClFtuaANz0fnPQ37WGnyEsEVHrmYy7Dwlsof8Ajy2ALK+5xtXanSxah9Gs+XQT0klSjw9rsOfJVgd/Da8/FInig0jrQ3mQdcflycPuANRMg06CmWv40ZM04orAX/BnpWvIj2FAMqiJVyca6SFEtXnHXuqntI9BbZgPC+mHkjzvFPkOFES4LOPzKdMoQQLXFxuuGNGtJCGweEwHCB5BrO0gzEUJH7C+E4bfBxGWCZ74KUCwncD/am7/NPEooMEjYLo6lV/Pk3+ECv7Q1hpB7s425iSMN872wjS/0tDPKGlyc4jR87hyNVTwIIQkYY+HSuJCpSFSK/ukrsYJfZ3g+8D4Tsd6kx9CHWj5nMlL4dX/pyLgqd/gAui3xBzgjAbsu5ymRzIwAuq33klVg9hrFCpAfX3TMtPirl7sgK7dXfoRnDyJBFVTyNaaWBkoxbqvHkeSHBnz0b4H3QN/fyHf88vGxCYkEJ1U4Uz9inJ0U+VLV3ISiK8vn7BBDTu4T97RB2o9J7+9JojQDxCOR7M=";
            var fixedTime = DateTime.Parse(timestamp).ToUniversalTime();

            var result = _verifier.VerifySignature(signature, timestamp, payload, fixedTime);
            Assert.True(result);
        }
    }
}
