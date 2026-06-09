package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.Map;

@Component
public class OrdersClient {
    private static final Logger log = LoggerFactory.getLogger(OrdersClient.class);
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_RESPONSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final WebClient http;
    private final BearerTokenProvider auth;
    private final Kount360Properties props;

    public OrdersClient(BearerTokenProvider auth, Kount360Properties props) {
        this.http = WebClient.builder().baseUrl(props.getApiBaseUrl()).build();
        this.auth = auth;
        this.props = props;
    }

    public Map<String, Object> postOrder(Map<String, Object> orderPayload) {
        String token = auth.getBearerToken();

        log.info("Posting order to Kount. apiBaseUrl={}, merchantOrderId={}",
                props.getApiBaseUrl(), orderPayload.get("merchantOrderId"));
        log.info("Using bearer token. length={}, prefix={}",
                token != null ? token.length() : 0,
                token != null ? token.substring(0, Math.min(20, token.length())) : "null");

        try {
            Map<String, Object> response = http.post()
                    .uri("/commerce/v2/orders?riskInquiry=true")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(orderPayload)
                    .retrieve()
                    .bodyToMono(MAP_RESPONSE_TYPE)
                    .block();

            log.info("Kount order post succeeded. merchantOrderId={}, responseKeys={}",
                    orderPayload.get("merchantOrderId"),
                    response != null ? response.keySet() : "null");

            return response;
        } catch (WebClientResponseException e) {
            log.error("Kount order post failed. status={}, responseBody={}",
                    e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw e;
        }
    }
}
