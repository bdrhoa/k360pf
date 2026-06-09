package com.example.nao;

import com.example.auth.BearerTokenProvider;
import com.example.k360pf.config.Kount360Properties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.Map;

@Component
public class NewAccountOpeningClient {
    private static final Logger log = LoggerFactory.getLogger(NewAccountOpeningClient.class);
    private static final ParameterizedTypeReference<Map<String, Object>> MAP_RESPONSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final WebClient http;
    private final BearerTokenProvider tokenProvider;
    private final Kount360Properties props;

    public NewAccountOpeningClient(BearerTokenProvider tokenProvider, Kount360Properties props) {
        this.http = WebClient.builder().baseUrl(props.getApiBaseUrl()).build();
        this.tokenProvider = tokenProvider;
        this.props = props;
    }

    public Map<String, Object> postNewAccountOpening(Map<String, Object> payload) {
        String bearerToken = tokenProvider.getBearerToken();

        log.info("Posting NAO V2 inquiry to Kount. apiBaseUrl={}, inquiryId={}",
                props.getApiBaseUrl(), payload.get("inquiryId"));

        try {
            Map<String, Object> response = http.post()
                    .uri("/newaccountopening/v2")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + bearerToken)
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(payload)
                    .retrieve()
                    .bodyToMono(MAP_RESPONSE_TYPE)
                    .block();

            log.info("Kount NAO V2 post succeeded. inquiryId={}, responseKeys={}",
                    payload.get("inquiryId"),
                    response != null ? response.keySet() : "null");

            return response;
        } catch (WebClientResponseException e) {
            log.error("Kount NAO V2 post failed. status={}, responseBody={}",
                    e.getStatusCode(), e.getResponseBodyAsString(), e);
            throw e;
        }
    }
}
