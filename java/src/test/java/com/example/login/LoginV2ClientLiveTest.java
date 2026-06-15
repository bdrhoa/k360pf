package com.example.login;

import com.example.auth.AuthClient;
import com.example.auth.BearerTokenProvider;
import com.example.k360pf.client.KountDecisionResponse;
import com.example.k360pf.config.Kount360Properties;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LoginV2ClientLiveTest {

    @Test
    void postLogin_liveApi_returnsDecisionResponse() {
        Assumptions.assumeTrue("true".equalsIgnoreCase(System.getenv("KOUNT_RUN_LIVE_TESTS")),
                "KOUNT_RUN_LIVE_TESTS=true not set; skipping live Login V2 test");

        String apiBaseUrl = "https://api-sandbox.kount.com";
        String authUrl = "https://login-uat.equifax.com/as/token";
        String apiKey = System.getenv("KOUNT_API_KEY");
        String channel = System.getenv("KOUNT_CHANNEL");

        Assumptions.assumeTrue(apiKey != null && !apiKey.isBlank(),
                "KOUNT_API_KEY not set; skipping live Login V2 test");

        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl(authUrl);
        props.setApiBaseUrl(apiBaseUrl);
        props.setApiKey(apiKey);
        props.setChannel(channel != null && !channel.isBlank() ? channel : "DEFAULT");

        BearerTokenProvider bearerTokenProvider = new AuthClient(props, WebClient.builder());
        LoginV2Client loginClient = new LoginV2Client(bearerTokenProvider, props);

        try {
            KountDecisionResponse response = loginClient.postLogin(buildPayload(props));

            assertNotNull(response, "Login V2 response should not be null");
            assertFalse(response.getBody().isEmpty(), "Login V2 response body should not be empty");
            assertTrue(Set.of("ALLOW", "BLOCK", "CHALLENGE").contains(response.getDecision()),
                    "Expected ALLOW, BLOCK, or CHALLENGE decision");
            if (response.isChallenge()) {
                assertNotNull(response.getCorrelationId(),
                        "CHALLENGE response should include x-correlation-id");
            }

            System.out.println("Live Login V2 response:");
            System.out.println(response.getBody());
        } catch (WebClientResponseException e) {
            Assumptions.assumeFalse(e.getStatusCode().is5xxServerError(),
                    "Kount Login V2 sandbox returned " + e.getStatusCode()
                            + "; responseBody=" + e.getResponseBodyAsString());
            throw e;
        }
    }

    private Map<String, Object> buildPayload(Kount360Properties props) {
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", UUID.randomUUID().toString().replace("-", ""));
        payload.put("channel", props.getChannel());
        payload.put("deviceSessionId", deviceSessionId);
        payload.put("userIp", "192.168.0.1");
        payload.put("loginUrl", "https://www.example.com/login");
        payload.put("person", Map.of(
                "name", Map.of(
                        "first", "John",
                        "last", "Doe",
                        "preferred", "Johnny"
                ),
                "emailAddress", "john.doe@example.com",
                "phoneNumber", "+12081234567",
                "addresses", List.of(Map.of(
                        "line1", "5813-5849 Quail Meadows Dr",
                        "line2", "",
                        "city", "Poplar Bluff",
                        "region", "CO",
                        "postalCode", "63901-0000",
                        "countryCode", "USA",
                        "addressType", "BILLING"
                ))
        ));
        payload.put("account", Map.of(
                "id", "meoyyd8za8jdmwfm",
                "type", "VIP",
                "creationDateTime", "2024-01-01T12:12:12.000Z",
                "username", "meoyyd8za8jdmwfm",
                "userPassword", "hashedpassword",
                "accountIsActive", true
        ));
        payload.put("strategy", Map.of(
                "mfaTemplateName", "default",
                "mfaTemplateValues", Map.of(
                        "firstName", "John",
                        "accountType", "VIP"
                )
        ));
        payload.put("customFields", Map.of(
                "exampleBoolean", true,
                "exampleNumber", 42,
                "exampleString", "Login Java live test"
        ));
        return payload;
    }
}
