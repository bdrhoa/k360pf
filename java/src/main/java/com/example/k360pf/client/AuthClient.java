package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class AuthClient {
    private final WebClient http;
    private final Kount360Properties props;

    private final AtomicReference<String> cachedToken = new AtomicReference<>(null);
    private volatile Instant tokenExpiry = Instant.EPOCH;

    public AuthClient(Kount360Properties props, WebClient.Builder builder) {
        this.props = props;
        this.http = builder.build();
    }

    public synchronized String getBearerToken() {
        if (now().isBefore(tokenExpiry.minusSeconds(30)) && cachedToken.get() != null) {
            return cachedToken.get();
        }

        // `props.getApiKey()` must already contain the Base64-encoded `clientId:clientSecret`
        // value used after `Basic ` in the Authorization header, matching the working curl command.
        Map<String, Object> resp = http.post()
                .uri(props.getAuthTokenUrl())
                .header(HttpHeaders.AUTHORIZATION, "Basic " + props.getApiKey())
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .body(BodyInserters
                        .fromFormData("grant_type", "client_credentials")
                        .with("scope", "k1_integration_api"))
                .retrieve()
                .bodyToMono(Map.class)
                .onErrorResume(err -> Mono.error(new RuntimeException("Auth error: " + err.getMessage(), err)))
                .block();

        if (resp == null || resp.get("access_token") == null) {
            throw new IllegalStateException("No access_token in auth response");
        }
        String token = (String) resp.get("access_token");
        Number expiresIn = (Number) resp.getOrDefault("expires_in", 300);
        tokenExpiry = now().plusSeconds(expiresIn.longValue());
        cachedToken.set(token);
        return token;
    }

    protected Instant now() {
        return Instant.now();
    }
}