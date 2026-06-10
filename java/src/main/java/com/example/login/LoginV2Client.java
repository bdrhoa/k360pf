package com.example.login;

import com.example.auth.BearerTokenProvider;
import com.example.k360pf.client.KountDecisionResponse;
import com.example.k360pf.config.Kount360Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import java.util.Objects;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

import java.util.Map;

@Component
public class LoginV2Client {
    private static final Logger log = LoggerFactory.getLogger(LoginV2Client.class);
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_RESPONSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final WebClient http;
    private final BearerTokenProvider tokenProvider;
    private final Kount360Properties props;

    public LoginV2Client(BearerTokenProvider tokenProvider, Kount360Properties props) {
        this(tokenProvider, props,
                WebClient.builder().baseUrl(Objects.requireNonNull(props.getApiBaseUrl(), "apiBaseUrl must not be null")).build());
    }

    LoginV2Client(BearerTokenProvider tokenProvider, Kount360Properties props, WebClient http) {
        this.http = http;
        this.tokenProvider = tokenProvider;
        this.props = props;
    }

    public KountDecisionResponse postLogin(Map<String, Object> payload) {
        String bearerToken = tokenProvider.getBearerToken();

        log.info("Posting Login V2 inquiry to Kount. apiBaseUrl={}, inquiryId={}",
                props.getApiBaseUrl(), payload.get("inquiryId"));

        try {
            KountDecisionResponse response = http.post()
                    .uri("/login/v2")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + bearerToken)
                    .contentType(Objects.requireNonNull(MediaType.APPLICATION_JSON, "applicationJson"))
                    .bodyValue(payload)
                    .exchangeToMono(clientResponse -> {
                        if (clientResponse.statusCode().isError()) {
                            return clientResponse.createException().flatMap(Mono::error);
                        }
                        return clientResponse
                                .bodyToMono(Objects.requireNonNull(MAP_RESPONSE_TYPE, "mapResponseType"))
                                .map(body -> new KountDecisionResponse(
                                        body,
                                        clientResponse.headers().asHttpHeaders().getFirst("x-correlation-id")));
                    })
                    .block();

            log.info("Kount Login V2 post succeeded. inquiryId={}, decision={}, correlationId={}",
                    payload.get("inquiryId"),
                    response != null ? response.getDecision() : "null",
                    response != null ? response.getCorrelationId() : "null");

            return response;
        } catch (WebClientResponseException e) {
            log.error("Kount Login V2 post failed. status={}, responseBody={}",
                    e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw e;
        }
    }
}
