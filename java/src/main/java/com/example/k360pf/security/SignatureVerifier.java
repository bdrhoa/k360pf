package com.example.k360pf.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.PSSParameterSpec;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.Base64;

@Component
public class SignatureVerifier {
    private static final Logger log = LoggerFactory.getLogger(SignatureVerifier.class);

    private final PublicKeyProvider keyProvider;
    private final Duration gracePeriod;

    @Autowired
    public SignatureVerifier(PublicKeyProvider keyProvider) {
        this(keyProvider, Duration.ofMinutes(5));
    }

    SignatureVerifier(PublicKeyProvider keyProvider, Duration gracePeriod) {
        this.keyProvider = keyProvider;
        this.gracePeriod = gracePeriod != null ? gracePeriod : Duration.ofMinutes(5);
    }

    /**
     * Verifies RSA-PSS (SHA-256) signature over timestamp + raw payload bytes.
     * Mirrors the .NET implementation:
     *  - throws IllegalArgumentException for bad input/signature/timestamp
     *  - throws IllegalStateException for public-key loading problems
     */
    public boolean verifySignature(String signatureBase64, String timestampIso8601, byte[] payload, Instant nowOverride) {
        if (signatureBase64 == null || signatureBase64.isEmpty()) {
            throw new IllegalArgumentException("Missing signature.");
        }

        final byte[] signatureBytes;
        try {
            signatureBytes = Base64.getDecoder().decode(signatureBase64);
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("Invalid base64 encoding in signature.");
        }

        final PublicKey publicKey;
        try {
            publicKey = keyProvider.getPublicKey();
        } catch (RuntimeException ex) {
            String message = ex.getMessage();
            if (message == null || message.isBlank()) {
                message = "Failed to load public key.";
            }
            throw new IllegalStateException(message, ex);
        }

        final Instant timestamp;
        try {
            timestamp = Instant.parse(timestampIso8601);
        } catch (DateTimeParseException ex) {
            throw new IllegalArgumentException("Invalid timestamp format.");
        }

        Instant now = nowOverride != null ? nowOverride : Instant.now();
        Duration delta = Duration.between(timestamp, now);
        if (delta.compareTo(gracePeriod) > 0) {
            throw new IllegalArgumentException("Timestamp too old.");
        }
        if (delta.compareTo(gracePeriod.negated()) < 0) {
            throw new IllegalArgumentException("Timestamp too new.");
        }

        byte[] timestampBytes = timestampIso8601.getBytes(StandardCharsets.UTF_8);
        byte[] digest = new byte[timestampBytes.length + payload.length];
        System.arraycopy(timestampBytes, 0, digest, 0, timestampBytes.length);
        System.arraycopy(payload, 0, digest, timestampBytes.length, payload.length);

        try {
            Signature sig = Signature.getInstance("RSASSA-PSS");

            PSSParameterSpec pss = new PSSParameterSpec("SHA-256", "MGF1", 
                new MGF1ParameterSpec("SHA-256"), 32, 1);

            sig.setParameter(pss);
            sig.initVerify(publicKey);
            sig.update(digest);

            boolean isValid = sig.verify(signatureBytes);
            if (!isValid) {
                log.warn("Signature verification failed: invalid signature.");
                throw new IllegalArgumentException("Signature verification failed.");
            }

            log.info("Signature successfully verified.");
            return true;
        } catch (IllegalArgumentException ex) {
            throw ex;
        } catch (Exception ex) {
            log.error("Signature verification failed: {}", ex.getMessage());
            throw new IllegalArgumentException("Signature verification failed.");
        }
    }

    public boolean verifySignature(String signatureBase64, String timestampIso8601, byte[] payload) {
        return verifySignature(signatureBase64, timestampIso8601, payload, null);
    }
}
