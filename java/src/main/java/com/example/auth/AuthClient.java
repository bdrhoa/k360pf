package com.example.auth;

import com.example.k360pf.config.Kount360AuthProperties;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicReference;

@Component
public class AuthClient implements BearerTokenProvider {
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_RESPONSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final WebClient http;
    private final Kount360AuthProperties authProperties;

    private final AtomicReference<String> cachedToken = new AtomicReference<>();
    private volatile Instant tokenExpiry = Instant.EPOCH;

    public AuthClient(Kount360AuthProperties authProperties, WebClient.Builder builder) {
        this.authProperties = authProperties;
        this.http = builder.build();
    }

    @Override
    public synchronized String getBearerToken() {
        if (now().isBefore(tokenExpiry.minusSeconds(30)) && cachedToken.get() != null) {
            return cachedToken.get();
        }

        // `authProperties.getApiKey()` must already contain the Base64-encoded `clientId:clientSecret`
        // value used after `Basic ` in the Authorization header, matching the working curl command.
        Map<String, Object> resp = http.post()
                .uri(Objects.requireNonNull(
                        authProperties.getAuthTokenUrl() != null ? authProperties.getAuthTokenUrl() : "",
                        "authTokenUrl"))
                .header(HttpHeaders.AUTHORIZATION, "Basic " + authProperties.getApiKey())
                .contentType(Objects.requireNonNull(
                        MediaType.APPLICATION_FORM_URLENCODED,
                        "applicationFormUrlencoded"))
                .body(BodyInserters
                        .fromFormData("grant_type", "client_credentials")
                        .with("scope", Objects.requireNonNull(authProperties.getAuthScope(), "authScope")))
                .retrieve()
                .bodyToMono(Objects.requireNonNull(MAP_RESPONSE_TYPE, "mapResponseType"))
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
