package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
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

    public AuthClient(Kount360Properties props) {
        this.props = props;
        this.http = WebClient.builder().build();
    }

    public synchronized String getBearerToken() {
        if (Instant.now().isBefore(tokenExpiry.minusSeconds(30)) && cachedToken.get() != null) {
            return cachedToken.get();
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "client_credentials");
        form.add("client_id", props.getClientId());
        form.add("client_secret", props.getApiKey());

        Map<String, Object> resp = http.post()
                .uri(props.getAuthTokenUrl())
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .bodyValue(form)
                .retrieve()
                .bodyToMono(Map.class)
                .onErrorResume(err -> Mono.error(new RuntimeException("Auth error: " + err.getMessage(), err)))
                .block();

        if (resp == null || resp.get("access_token") == null) {
            throw new IllegalStateException("No access_token in auth response");
        }
        String token = (String) resp.get("access_token");
        Number expiresIn = (Number) resp.getOrDefault("expires_in", 300);
        tokenExpiry = Instant.now().plusSeconds(expiresIn.longValue());
        cachedToken.set(token);
        return token;
    }
}
