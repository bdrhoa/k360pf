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
    }
}