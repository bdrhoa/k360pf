package com.example.k360pf.security;

import com.example.k360pf.client.AuthClient;
import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class PublicKeyProvider {
    private final Kount360Properties props;
    private final AuthClient auth;
    private final WebClient http = WebClient.builder().build();
    private final AtomicReference<PublicKey> cachedKey = new AtomicReference<>();
    private volatile Instant nextRefresh = Instant.EPOCH;

    public PublicKeyProvider(Kount360Properties props, AuthClient auth) {
        this.props = props;
        this.auth = auth;
    }

    public PublicKey getPublicKey() {
        if (cachedKey.get() != null && Instant.now().isBefore(nextRefresh)) {
            return cachedKey.get();
        }
        try {
            PublicKey pk;
            if (props.getPublicKeyPem() != null && !props.getPublicKeyPem().isEmpty()) {
                pk = parsePem(props.getPublicKeyPem());
            } else if (props.getPublicKeyUrl() != null && !props.getPublicKeyUrl().isEmpty()) {
                var req = http.get().uri(props.getPublicKeyUrl());
                try {
                    String token = auth.getBearerToken();
                    req = req.header(HttpHeaders.AUTHORIZATION, "Bearer " + token);
                } catch (Exception ignored) {}
                String pem = req.retrieve().bodyToMono(String.class).block();
                pk = parsePem(pem);
            } else {
                throw new IllegalStateException("No public key configured. Set K360_PUBLIC_KEY_PEM or K360_PUBLIC_KEY_URL.");
            }
            cachedKey.set(pk);
            nextRefresh = Instant.now().plusSeconds((long) props.getPublicKeyRefreshMinutes() * 60L);
            return pk;
        } catch (Exception e) {
            throw new RuntimeException("Failed to load public key: " + e.getMessage(), e);
        }
    }

    private static PublicKey parsePem(String pem) throws Exception {
        String clean = pem.replace("-----BEGIN PUBLIC KEY-----", "")
                .replace("-----END PUBLIC KEY-----", "")
                .replaceAll("\n|\r", "").trim();
        byte[] der = Base64.getDecoder().decode(clean);
        X509EncodedKeySpec spec = new X509EncodedKeySpec(der);
        return KeyFactory.getInstance("RSA").generatePublic(spec);
    }
}
