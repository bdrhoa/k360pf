package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

import org.springframework.web.reactive.function.client.WebClient;

public class AuthClientRefreshVerifier {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    public static void main(String[] args) throws Exception {
        String authUrl = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token";
        String clientId = System.getenv("KOUNT_CLIENT_ID");
        String apiKey = System.getenv("KOUNT_API_KEY");

        if (clientId == null || clientId.isBlank()) {
            throw new IllegalStateException("KOUNT_CLIENT_ID not set");
        }
        if (apiKey == null || apiKey.isBlank()) {
            throw new IllegalStateException("KOUNT_API_KEY not set");
        }

        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl(authUrl);
        props.setClientId(clientId);
        props.setApiKey(apiKey);

        AuthClient authClient = new AuthClient(props, WebClient.builder());

        Instant start = Instant.now();
        String firstToken = authClient.getBearerToken();
        Instant firstIssuedAt = Instant.now();

        System.out.println("Initial token acquired at: " + firstIssuedAt);
        printJwtTimes("Initial token", firstToken);

        String currentToken = firstToken;
        Instant refreshDetectedAt = null;

        // Poll every 15 seconds for up to 25 minutes
        Instant deadline = start.plus(Duration.ofMinutes(25));
        while (Instant.now().isBefore(deadline)) {
            Thread.sleep(Duration.ofSeconds(15).toMillis());

            String token = authClient.getBearerToken();
            Instant now = Instant.now();

            if (!token.equals(currentToken)) {
                refreshDetectedAt = now;
                System.out.println();
                System.out.println("Token change detected at: " + refreshDetectedAt);
                printJwtTimes("Refreshed token", token);

                Duration elapsed = Duration.between(firstIssuedAt, refreshDetectedAt);
                long elapsedSeconds = elapsed.getSeconds();

                System.out.println("Elapsed seconds before refresh: " + elapsedSeconds);

                // Expected refresh threshold is roughly 1170 seconds for a 1200-second token
                if (elapsedSeconds < 1100) {
                    throw new IllegalStateException(
                            "Token refreshed too early. Expected roughly near 1170s, actual: " + elapsedSeconds + "s");
                }
                if (elapsedSeconds > 1210) {
                    throw new IllegalStateException(
                            "Token refreshed too late. Expected before expiry, actual: " + elapsedSeconds + "s");
                }

                System.out.println("Refresh timing looks correct.");
                return;
            }

            System.out.println("[" + now + "] token unchanged");
        }

        throw new IllegalStateException("No token refresh detected within 25 minutes.");
    }

    private static void printJwtTimes(String label, String jwt) throws Exception {
        System.out.println("JWT: " + jwt);
        String[] parts = jwt.split("\\.");
        if (parts.length != 3) {
            throw new IllegalArgumentException(label + " is not a JWT");
        }

        String payloadJson = new String(Base64.getUrlDecoder().decode(padBase64(parts[1])), StandardCharsets.UTF_8);
        @SuppressWarnings("unchecked")
        Map<String, Object> payload = OBJECT_MAPPER.readValue(payloadJson, Map.class);

        Number iat = (Number) payload.get("iat");
        Number exp = (Number) payload.get("exp");

        System.out.println(label + " iat: " + iat + " (" + Instant.ofEpochSecond(iat.longValue()) + ")");
        System.out.println(label + " exp: " + exp + " (" + Instant.ofEpochSecond(exp.longValue()) + ")");
        System.out.println(label + " lifetime seconds: " + (exp.longValue() - iat.longValue()));
    }

    private static String padBase64(String value) {
        int padding = (4 - (value.length() % 4)) % 4;
        return value + "=".repeat(padding);
    }
}