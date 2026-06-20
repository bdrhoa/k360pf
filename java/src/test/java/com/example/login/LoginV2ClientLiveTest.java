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
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class LoginV2ClientLiveTest {

    @Test
    void postLogin_liveApi_allowResponse_simulatesLoginAllowed() {
        KountDecisionResponse response = postLoginLive("https://www.example.com/login");

        assertEquals("ALLOW", response.getDecision(), "Expected ALLOW decision");
        System.out.println("login allowed");
        printResponse(response);
    }

    @Test
    void postLogin_liveApi_blockResponse_simulatesLoginNotAllowed() {
        KountDecisionResponse response = postLoginLive("https://www.example.com/block");

        assertEquals("BLOCK", response.getDecision(), "Expected BLOCK decision");
        System.out.println("login not allowed");
        printResponse(response);
    }

    @Test
    void postLogin_liveApi_challengeResponse_stubsChallengeBehavior() {
        KountDecisionResponse response = postLoginLive("https://www.example.com/challenge");

        assertEquals("CHALLENGE", response.getDecision(), "Expected CHALLENGE decision");
        System.out.println("challenge response");
        printResponse(response);
    }

    private KountDecisionResponse postLoginLive(String loginUrl) {
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
            KountDecisionResponse response = loginClient.postLogin(buildPayload(props, loginUrl));

            assertNotNull(response, "Login V2 response should not be null");
            assertFalse(response.getBody().isEmpty(), "Login V2 response body should not be empty");
            return response;
        } catch (WebClientResponseException e) {
            Assumptions.assumeFalse(e.getStatusCode().is5xxServerError(),
                    "Kount Login V2 sandbox returned " + e.getStatusCode()
                            + "; responseBody=" + e.getResponseBodyAsString());
            throw e;
        }
    }

    private void printResponse(KountDecisionResponse response) {
        System.out.println("Live Login V2 response:");
        System.out.println(response.getBody());
    }

    private Map<String, Object> buildPayload(Kount360Properties props, String loginUrl) {
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", UUID.randomUUID().toString().replace("-", ""));
        payload.put("channel", props.getChannel());
        payload.put("deviceSessionId", deviceSessionId);
        payload.put("userIp", "192.168.0.1");
        payload.put("loginUrl", loginUrl);
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
