package com.example.login;

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
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LoginV2ClientTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private TestHttpServer server;

    @AfterEach
    void stopServer() {
        if (server != null) {
            server.stop();
        }
    }

    @Test
    void postLogin_postsBodyAndParsesAllow() throws Exception {
        server = TestHttpServer.start(Map.of("decision", "ALLOW"));
        LoginV2Client client = new LoginV2Client(() -> "test-token", props(server.baseUrl()));

        Map<String, Object> payload = loginPayload();
        KountDecisionResponse response = client.postLogin(payload);

        assertEquals("ALLOW", response.getDecision());
        assertTrue(response.isAllow());

        RecordedRequest request = server.singleRequest();
        assertEquals("POST", request.method());
        assertEquals("/login/v2", request.path());
        assertEquals("Bearer test-token", request.header("Authorization"));
        assertTrue(request.header("Content-Type").startsWith("application/json"));
        assertEquals("login-test", request.json().get("inquiryId"));
        assertEquals("DEFAULT", request.json().get("channel"));
        assertEquals("session123", request.json().get("deviceSessionId"));
        assertEquals("192.168.0.1", request.json().get("userIp"));
        assertEquals("https://www.example.com/login", request.json().get("loginUrl"));
        assertNotNull(request.json().get("person"));
        assertNotNull(request.json().get("account"));
        assertNotNull(request.json().get("strategy"));
        assertNotNull(request.json().get("customFields"));
    }

    @Test
    void postLogin_parsesBlock() throws Exception {
        server = TestHttpServer.start(Map.of("decision", "BLOCK"));
        LoginV2Client client = new LoginV2Client(() -> "test-token", props(server.baseUrl()));

        KountDecisionResponse response = client.postLogin(loginPayload());

        assertEquals("BLOCK", response.getDecision());
        assertTrue(response.isBlock());
    }

    @Test
    void postLogin_parsesChallengeCorrelationHeader() throws Exception {
        String correlationId = UUID.randomUUID().toString();
        server = TestHttpServer.start(Map.of("decision", "CHALLENGE"), correlationId);
        LoginV2Client client = new LoginV2Client(() -> "test-token", props(server.baseUrl()));

        KountDecisionResponse response = client.postLogin(loginPayload());

        assertEquals("CHALLENGE", response.getDecision());
        assertTrue(response.isChallenge());
        assertEquals(correlationId, response.getCorrelationId());
    }

    private static Kount360Properties props(String baseUrl) {
        Kount360Properties props = new Kount360Properties();
        props.setApiBaseUrl(baseUrl);
        return props;
    }

    private static Map<String, Object> loginPayload() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "login-test");
        payload.put("channel", "DEFAULT");
        payload.put("deviceSessionId", "session123");
        payload.put("userIp", "192.168.0.1");
        payload.put("loginUrl", "https://www.example.com/login");
        payload.put("person", Map.of(
                "emailAddress", "john.doe@example.com",
                "phoneNumber", "+12081234567"
        ));
        payload.put("account", Map.of(
                "id", "account-123",
                "type", "VIP",
                "username", "john.doe",
                "accountIsActive", true
        ));
        payload.put("strategy", Map.of(
                "mfaTemplateName", "default",
                "mfaTemplateValues", Map.of("firstName", "John")
        ));
        payload.put("customFields", Map.of("exampleString", "Login Java test"));
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

        static TestHttpServer start(Map<String, Object> responseBody) throws IOException {
            return start(responseBody, null);
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
            if (correlationId != null) {
                exchange.getResponseHeaders().add("x-correlation-id", correlationId);
            }
            exchange.sendResponseHeaders(200, response.length);
            try (OutputStream output = exchange.getResponseBody()) {
                output.write(response);
            }
        }
    }
}
