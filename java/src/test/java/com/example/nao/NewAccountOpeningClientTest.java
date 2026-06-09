package com.example.nao;

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
import static org.junit.jupiter.api.Assertions.assertTrue;

class NewAccountOpeningClientTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private TestHttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop();
        }
    }

    @Test
    void postNewAccountOpening_parsesChallengeCorrelationHeader() throws Exception {
        String correlationId = UUID.randomUUID().toString();
        server = TestHttpServer.start(Map.of("decision", "CHALLENGE"), correlationId);
        NewAccountOpeningClient client = new NewAccountOpeningClient(() -> "test-token", props(server.baseUrl()));

        KountDecisionResponse response = client.postNewAccountOpening(naoPayload());

        assertEquals("CHALLENGE", response.getDecision());
        assertTrue(response.isChallenge());
        assertEquals(correlationId, response.getCorrelationId());

        RecordedRequest request = server.singleRequest();
        assertEquals("POST", request.method());
        assertEquals("/newaccountopening/v2", request.path());
        assertEquals("Bearer test-token", request.header("Authorization"));
        assertTrue(request.header("Content-Type").startsWith("application/json"));
        assertEquals("nao-test", request.json().get("inquiryId"));
    }

    private static Kount360Properties props(String baseUrl) {
        Kount360Properties props = new Kount360Properties();
        props.setApiBaseUrl(baseUrl);
        return props;
    }

    private static Map<String, Object> naoPayload() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "nao-test");
        payload.put("channel", "DEFAULT");
        payload.put("deviceSessionId", "session123");
        payload.put("userIp", "192.168.0.1");
        payload.put("accountCreationUrl", "https://www.example.com/create-account");
        payload.put("person", Map.of("emailAddress", "john.doe@example.com"));
        payload.put("account", Map.of("id", "account-123", "username", "john.doe"));
        payload.put("strategy", Map.of("verificationTemplateName", "default"));
        payload.put("customFields", Map.of("exampleString", "NAO Java test"));
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

        static TestHttpServer start(Map<String, Object> responseBody, String correlationId) throws IOException {
            HttpServer httpServer = HttpServer.create(new InetSocketAddress(0), 0);
            TestHttpServer server = new TestHttpServer(httpServer);
            httpServer.createContext("/", exchange -> server.handle(exchange, responseBody, correlationId));
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

        private void handle(HttpExchange exchange, Map<String, Object> responseBody, String correlationId) throws IOException {
            String body = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
            requests.add(new RecordedRequest(
                    exchange.getRequestMethod(),
                    exchange.getRequestURI().getPath(),
                    exchange.getRequestHeaders(),
                    body));

            byte[] response = OBJECT_MAPPER.writeValueAsBytes(responseBody);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.getResponseHeaders().add("X-Correlation-Id", correlationId);
            exchange.sendResponseHeaders(200, response.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(response);
            }
        }
    }
}
