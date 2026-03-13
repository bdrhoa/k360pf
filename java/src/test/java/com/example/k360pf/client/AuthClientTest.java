package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.ClientResponse;
import org.springframework.web.reactive.function.client.ExchangeFunction;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;

class AuthClientTest {

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void getBearerToken_fetchesAndCachesToken() throws Exception {
        // Arrange: fake config
        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl("https://auth.example.com/oauth2/token");
        props.setClientId("client-id");
        props.setApiKey("secret");

        AtomicInteger callCount = new AtomicInteger(0);

        // Stub ExchangeFunction that returns a fake token JSON
        ExchangeFunction exchangeFunction = request -> {
            callCount.incrementAndGet();

            Map<String, Object> body = Map.of(
                    "access_token", "abc123",
                    "token_type", "Bearer",
                    "expires_in", 3600
            );

            String json;
            try {
                json = objectMapper.writeValueAsString(body);
            } catch (Exception e) {
                return Mono.error(e);
            }

            ClientResponse response = ClientResponse
                    .create(HttpStatus.OK)
                    .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                    .body(json)
                    .build();

            return Mono.just(response);
        };

        WebClient.Builder builder = WebClient.builder().exchangeFunction(exchangeFunction);

        AuthClient authClient = new AuthClient(props, builder);

        // Act
        String token1 = authClient.getBearerToken();
        String token2 = authClient.getBearerToken();  // should hit cache

        // Assert
        assertEquals("abc123", token1);
        assertSame(token1, token2, "Token should be cached and reused");
        assertEquals(1, callCount.get(), "Auth endpoint should be called only once");
    }
}