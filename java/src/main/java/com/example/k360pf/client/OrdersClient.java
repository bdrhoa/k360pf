package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

@Component
public class OrdersClient {
    private final WebClient http;
    private final AuthClient auth;
    private final Kount360Properties props;

    public OrdersClient(AuthClient auth, Kount360Properties props) {
        this.http = WebClient.builder().baseUrl(props.getApiBaseUrl()).build();
        this.auth = auth;
        this.props = props;
    }

    public Map<String, Object> postOrder(Map<String, Object> orderPayload) {
        String token = auth.getBearerToken();
        return http.post()
                .uri("/commerce/v2/orders")
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(orderPayload)
                .retrieve()
                .bodyToMono(Map.class)
                .block();
    }
}
