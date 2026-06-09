package com.example.k360pf.security;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.stereotype.Component;

import java.security.KeyFactory;
import java.security.PublicKey;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

@Component
public class PublicKeyProvider {
    private static final Logger log = LoggerFactory.getLogger(SignatureVerifier.class);
    private final Kount360Properties props;

    public PublicKeyProvider(Kount360Properties props) {
        this.props = props;
    }


    public PublicKey getPublicKey() {

         if (props.getPublicKey() != null) {
            log.info(props.getPublicKey());
            PublicKey pk = loadPublicKey(props.getPublicKey());
            return pk;
         }
        else {
                throw new IllegalStateException("No public key configured. Set KOUNT_PUBLIC_KEY");
         }
    }
    
    /**
     * Loads the RSA public key from base64 encoded string
     */
    private static PublicKey loadPublicKey(String publicKeyBase64) {
        try {
            byte[] keyBytes = Base64.getDecoder().decode(publicKeyBase64);
            X509EncodedKeySpec spec = new X509EncodedKeySpec(keyBytes);
            KeyFactory keyFactory = KeyFactory.getInstance("RSA");
            return keyFactory.generatePublic(spec);
        } catch (Exception e) {
            throw new RuntimeException("Failed to load public key", e);
        }
    }

}

    /*

There is no public end point to get the public key. So the following logic can be used once a plublic end point is available.@interface
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

*/
