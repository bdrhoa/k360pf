package com.example.events;

import com.example.auth.BearerTokenProvider;
import com.example.k360pf.client.KountDecisionResponse;
import com.example.k360pf.config.Kount360Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

@Component
public class KountEventsClient {
    private static final Logger log = LoggerFactory.getLogger(KountEventsClient.class);
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_RESPONSE_TYPE =
            new ParameterizedTypeReference<Map<String, Object>>() {
            };

    private final WebClient http;
    private final BearerTokenProvider tokenProvider;
    private final Kount360Properties props;

    public KountEventsClient(BearerTokenProvider tokenProvider, Kount360Properties props) {
        this(tokenProvider, props,
                WebClient.builder().baseUrl(Objects.requireNonNull(props.getApiBaseUrl(), "apiBaseUrl")).build());
    }

    KountEventsClient(BearerTokenProvider tokenProvider, Kount360Properties props, WebClient http) {
        this.http = http;
        this.tokenProvider = tokenProvider;
        this.props = props;
    }

    public Map<String, Object> postFailedAttempt(Map<String, Object> payload) {
        return postEvent("/events/failed-attempt", payload);
    }

    public Map<String, Object> postChallengeOutcome(Map<String, Object> payload) {
        return postEvent("/events/challenge-outcome", payload);
    }

    public Map<String, Object> postChallengeOutcome(KountDecisionResponse decisionResponse, Map<String, Object> payload) {
        if (decisionResponse == null || decisionResponse.getCorrelationId() == null
                || decisionResponse.getCorrelationId().isBlank()) {
            throw new IllegalArgumentException("challenge-outcome requires a decision response correlationId");
        }
        if (!decisionResponse.isChallenge()) {
            throw new IllegalArgumentException("challenge-outcome requires a CHALLENGE decision response");
        }

        Map<String, Object> eventPayload = new LinkedHashMap<>(payload);
        eventPayload.put("decisionCorrelationId", decisionResponse.getCorrelationId());
        return postChallengeOutcome(eventPayload);
    }

    private Map<String, Object> postEvent(String path, Map<String, Object> payload) {
        String bearerToken = tokenProvider.getBearerToken();

        log.info("Posting Kount event. apiBaseUrl={}, path={}, inquiryId={}",
                props.getApiBaseUrl(), path, payload.get("inquiryId"));

        try {
            Map<String, Object> response = http.post()
                    .uri(Objects.requireNonNull(path, "path"))
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + bearerToken)
                    .contentType(Objects.requireNonNull(MediaType.APPLICATION_JSON, "applicationJson"))
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(Objects.requireNonNull(MAP_RESPONSE_TYPE, "mapResponseType"))
                    .block();

            log.info("Kount event post succeeded. path={}, inquiryId={}, responseKeys={}",
                    path,
                    payload.get("inquiryId"),
                    response != null ? response.keySet() : "null");

            return response;
        } catch (WebClientResponseException e) {
            log.error("Kount event post failed. path={}, status={}, responseBody={}",
                    path, e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw e;
        }
    }
}
