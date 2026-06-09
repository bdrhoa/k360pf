package com.example.events;

import com.example.k360pf.client.KountDecisionResponse;
import com.example.k360pf.config.Kount360Properties;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;

class KountEventsClientTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private TestHttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop();
        }
    }

    @Test
    void postChallengeOutcome_postsCorrelationIdFromChallengeDecision() throws Exception {
        server = TestHttpServer.start();
        KountEventsClient client = new KountEventsClient(() -> "test-token", props(server.baseUrl()));
        String correlationId = UUID.randomUUID().toString();
        KountDecisionResponse challengeResponse = new KountDecisionResponse(
                Map.of("decision", "CHALLENGE"),
                correlationId);

        Map<String, Object> payload = challengeOutcomePayload();
        client.postChallengeOutcome(challengeResponse, payload);

        RecordedRequest request = server.singleRequest();
        assertEquals("POST", request.method());
        assertEquals("/events/challenge-outcome", request.path());
        assertEquals("Bearer test-token", request.header("Authorization"));
        assertEquals("application/json", request.header("Content-Type"));
        assertEquals(correlationId, request.json().get("decisionCorrelationId"));
    }

    @Test
    void postFailedAttempt_postsToFailedAttemptEndpoint() throws Exception {
        server = TestHttpServer.start();
        KountEventsClient client = new KountEventsClient(() -> "test-token", props(server.baseUrl()));

        client.postFailedAttempt(failedAttemptPayload());

        RecordedRequest request = server.singleRequest();
        assertEquals("POST", request.method());
        assertEquals("/events/failed-attempt", request.path());
        assertEquals("Bearer test-token", request.header("Authorization"));
        assertEquals("application/json", request.header("Content-Type"));
        assertEquals("failed-attempt-test", request.json().get("inquiryId"));
    }

    private static Kount360Properties props(String baseUrl) {
        Kount360Properties props = new Kount360Properties();
        props.setApiBaseUrl(baseUrl);
        return props;
    }

    private static Map<String, Object> challengeOutcomePayload() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "challenge-outcome-test");
        payload.put("deviceSessionId", "session123");
        payload.put("challengeType", "Captcha");
        payload.put("challengeStatus", "Success");
        payload.put("sentTimestamp", "2024-02-22T01:02:03.123Z");
        payload.put("completedTimestamp", "2024-02-22T01:03:03.123Z");
        return payload;
    }

    private static Map<String, Object> failedAttemptPayload() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "failed-attempt-test");
        payload.put("channel", "DEFAULT");
        payload.put("deviceSessionId", "session123");
        payload.put("userIp", "192.168.0.1");
        payload.put("loginUrl", "https://www.example.com/login");
        payload.put("person", Map.of("emailAddress", "john.doe@example.com"));
        payload.put("account", Map.of("id", "account-123", "username", "john.doe"));
        return payload;
    }

    private record RecordedRequest(String method, String path, Map<String, List<String>> headers, String body) {
        String header(String name) {
            return headers.entrySet().stream()
                    .filter(entry -> entry.getKey().equalsIgnoreCase(name))
                    .flatMap(entry -> entry.getValue().stream())
                    .findFirst()
                    .orElse(null);
        }

        Map<String, Object> json() throws IOException {
            return OBJECT_MAPPER.readValue(body, new TypeReference<>() {
            });
        }
    }

    private static class TestHttpServer {
        private final HttpServer httpServer;
        private final List<RecordedRequest> requests = new ArrayList<>();

        private TestHttpServer(HttpServer httpServer) {
            this.httpServer = httpServer;
        }

        static TestHttpServer start() throws IOException {
            HttpServer httpServer = HttpServer.create(new InetSocketAddress(0), 0);
            TestHttpServer server = new TestHttpServer(httpServer);
            httpServer.createContext("/", server::handle);
            httpServer.start();
            return server;
        }

        String baseUrl() {
            return "http://localhost:" + httpServer.getAddress().getPort();
        }

        RecordedRequest singleRequest() {
            assertEquals(1, requests.size());
            return requests.getFirst();
        }

        void stop() {
            httpServer.stop(0);
        }

        private void handle(HttpExchange exchange) throws IOException {
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            requests.add(new RecordedRequest(
                    exchange.getRequestMethod(),
                    exchange.getRequestURI().getPath(),
                    exchange.getRequestHeaders(),
                    body));

            byte[] response = OBJECT_MAPPER.writeValueAsBytes(Map.of());
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, response.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(response);
            }
        }
    }
}
