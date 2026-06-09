package com.example.nao;

import com.example.auth.AuthClient;
import com.example.k360pf.config.Kount360Properties;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class NAOClientLiveTest {

    @Test
    void postNewAccountOpening_liveApi_returnsResponse() {
        String apiBaseUrl = "https://api-sandbox.kount.com";
        String authUrl = "https://login-uat.equifax.com/as/token";
        String clientId = System.getenv("KOUNT_CLIENT_ID");
        String apiKey = System.getenv("KOUNT_API_KEY");
        String channel = System.getenv("KOUNT_CHANNEL");

        Assumptions.assumeTrue(authUrl != null && !authUrl.isBlank(),
                "KOUNT_AUTH_TOKEN_URL not set; skipping live NAO test");
        Assumptions.assumeTrue(apiBaseUrl != null && !apiBaseUrl.isBlank(),
                "KOUNT_API_BASE_URL not set; skipping live NAO test");
        Assumptions.assumeTrue(apiKey != null && !apiKey.isBlank(),
                "KOUNT_API_KEY not set; skipping live NAO test");

        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl(authUrl);
        props.setApiBaseUrl(apiBaseUrl);
        props.setClientId(clientId);
        props.setApiKey(apiKey);
        props.setChannel(channel != null && !channel.isBlank() ? channel : "DEFAULT");

        AuthClient authClient = new AuthClient(props, org.springframework.web.reactive.function.client.WebClient.builder());
        NewAccountOpeningClient naoClient = new NewAccountOpeningClient(authClient, props);

        Map<String, Object> payload = buildPayload(props);

        Map<String, Object> response = naoClient.postNewAccountOpening(payload);

        assertNotNull(response, "NAO API response should not be null");
        assertFalse(response.isEmpty(), "NAO API response should not be empty");

        System.out.println("Live NAO response:");
        System.out.println(response);
    }

    private Map<String, Object> buildPayload(Kount360Properties props) {
        String inquiryId = "nao-live-" + UUID.randomUUID();
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", inquiryId);
        payload.put("channel", props.getChannel());
        payload.put("deviceSessionId", deviceSessionId);
        payload.put("userIp", "192.168.0.1");
        payload.put("accountCreationUrl", "https://www.example.com/create-account");

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
                "id", "11223dr44",
                "type", "VIP",
                "username", "meoyyd8za8jdmwfm"
        ));

        payload.put("strategy", Map.of(
                "verificationTemplateName", "default",
                "verificationTemplateValues", Map.of(
                        "firstName", "John",
                        "accountType", "VIP"
                )
        ));

        payload.put("customFields", Map.of(
                "exampleBoolean", true,
                "exampleNumber", 42,
                "exampleString", "NAO Java live test"
        ));

        if (props.getClientId() != null && !props.getClientId().isBlank()) {
            payload.put("sharedContext", Map.of(
                    "sourceClientId", props.getClientId(),
                    "sourceDeviceSessionId", deviceSessionId
            ));
        }

        return payload;
    }
}
