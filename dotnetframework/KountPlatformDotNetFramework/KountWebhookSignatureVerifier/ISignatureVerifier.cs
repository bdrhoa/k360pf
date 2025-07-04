using System;

namespace WebhookSignatureVerifier.Services
{
    public interface ISignatureVerifier
    {
        bool VerifySignature(string signatureBase64, string timestampIso8601, byte[] payload, DateTime? nowOverride = null);
    }
}