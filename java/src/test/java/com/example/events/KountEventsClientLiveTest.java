package com.example.events;

import com.example.auth.AuthClient;
import com.example.auth.BearerTokenProvider;
import com.example.k360pf.config.Kount360Properties;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertNotNull;

class KountEventsClientLiveTest {

    @Test
    void postFailedAttempt_liveApi_returnsResponse() {
        Assumptions.assumeTrue("true".equalsIgnoreCase(System.getenv("KOUNT_RUN_LIVE_TESTS")),
                "KOUNT_RUN_LIVE_TESTS=true not set; skipping live failed-attempt test");

        String apiBaseUrl = "https://api-sandbox.kount.com";
        String authUrl = "https://login-uat.equifax.com/as/token";
        String apiKey = System.getenv("KOUNT_API_KEY");
        String channel = System.getenv("KOUNT_CHANNEL");

        Assumptions.assumeTrue(apiKey != null && !apiKey.isBlank(),
                "KOUNT_API_KEY not set; skipping live failed-attempt test");

        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl(authUrl);
        props.setApiBaseUrl(apiBaseUrl);
        props.setApiKey(apiKey);
        props.setChannel(channel != null && !channel.isBlank() ? channel : "DEFAULT");

        BearerTokenProvider bearerTokenProvider = new AuthClient(props, WebClient.builder());
        KountEventsClient eventsClient = new KountEventsClient(bearerTokenProvider, props);

        try {
            Map<String, Object> response = eventsClient.postFailedAttempt(buildPayload(props));

            assertNotNull(response, "failed-attempt event response should not be null");
            System.out.println("Live failed-attempt response:");
            System.out.println(response);
        } catch (WebClientResponseException e) {
            Assumptions.assumeFalse(e.getStatusCode().is5xxServerError(),
                    "Kount failed-attempt sandbox returned " + e.getStatusCode()
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
                "emailAddress", "john.doe@example.com",
                "phoneNumber", "+12081234567",
                "name", Map.of(
                        "first", "John",
                        "last", "Doe",
                        "preferred", "Johnny"
                ),
                "addresses", List.of(Map.of(
                        "line1", "5813-5849 Quail Meadows Dr",
                        "line2", "",
                        "city", "Poplar Bluff",
                        "region", "CO",
                        "postalCode", "63901-0000",
                        "countryCode", "USA",
                        "addressType", "UNKNOWN_ADDRESS_TYPE"
                ))
        ));
        payload.put("account", Map.of(
                "id", "11223dr44",
                "username", "meoyyd8za8jdmwfm",
                "type", "VIP",
                "creationDateTime", "2024-01-01T12:12:12.000Z",
                "userPassword", "hashedpassword",
                "accountIsActive", true
        ));
        return payload;
    }
}
