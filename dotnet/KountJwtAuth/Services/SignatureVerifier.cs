using System;
using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Logging;

namespace KountJwtAuth.Services
{
    public class SignatureVerifier
    {
        private readonly ILogger<SignatureVerifier> _logger;
        private readonly TimeSpan _gracePeriod;

        public SignatureVerifier(ILogger<SignatureVerifier> logger, TimeSpan? gracePeriod = null)
        {
            _logger = logger;
            _gracePeriod = gracePeriod ?? TimeSpan.FromMinutes(5);
        }

        public bool VerifySignature(string signatureBase64, string timestampIso8601, byte[] payload, DateTime? nowOverride = null)
        {
            // 1. Validate and decode signature
            if (string.IsNullOrEmpty(signatureBase64))
                throw new ArgumentException("Missing signature.");

            byte[] signature;
            try
            {
                signature = Convert.FromBase64String(signatureBase64);
            }
            catch (FormatException)
            {
                throw new ArgumentException("Invalid base64 encoding in signature.");
            }

            // 2. Get public key from environment
            var publicKeyBase64 = Environment.GetEnvironmentVariable("KOUNT_PUBLIC_KEY");
            if (string.IsNullOrEmpty(publicKeyBase64))
                throw new InvalidOperationException("KOUNT_PUBLIC_KEY environment variable not set.");

            byte[] publicKeyDer;
            try
            {
                publicKeyDer = Convert.FromBase64String(publicKeyBase64);
            }
            catch (FormatException)
            {
                throw new InvalidOperationException("Invalid base64 encoding in public key.");
            }

            // 3. Parse timestamp
            DateTime timestamp;
            try
            {
                timestamp = DateTime.Parse(timestampIso8601).ToUniversalTime();
            }
            catch (FormatException)
            {
                throw new ArgumentException("Invalid timestamp format.");
            }

            var now = nowOverride ?? DateTime.UtcNow;
            var delta = now - timestamp;
            if (delta > _gracePeriod)
                throw new ArgumentException("Timestamp too old.");
            if (delta < -_gracePeriod)
                throw new ArgumentException("Timestamp too new.");

            // 4. Combine timestamp and payload
            var digest = Encoding.UTF8.GetBytes(timestampIso8601).Concat(payload).ToArray();

            // 5. Verify signature using RSA-PSS
            try
            {
                using var rsa = RSA.Create();
                rsa.ImportSubjectPublicKeyInfo(publicKeyDer, out _);
                var isValid = rsa.VerifyData(digest, signature, HashAlgorithmName.SHA256, RSASignaturePadding.Pss);
                if (!isValid)
                {
                    _logger.LogWarning("Signature verification failed: invalid signature.");
                    throw new ArgumentException("Signature verification failed.");
                }

                _logger.LogInformation("Signature successfully verified.");
                return true;
            }
            catch (CryptographicException ex)
            {
                _logger?.LogError("Signature verification failed: {Message}", ex.Message);
                throw new ArgumentException("Signature verification failed.");
            }
        }
    }
}