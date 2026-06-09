package com.example.nao;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/demo/nao")
public class NewAccountOpeningController {
    private final NewAccountOpeningClient naoClient;
    private final Kount360Properties props;

    public NewAccountOpeningController(NewAccountOpeningClient naoClient, Kount360Properties props) {
        this.naoClient = naoClient;
        this.props = props;
    }

    @PostMapping
    public ResponseEntity<?> sendDemoNewAccountOpening() {
        Map<String, Object> payload = buildDemoPayload();
        Map<String, Object> response = naoClient.postNewAccountOpening(payload);
        return ResponseEntity.ok(response);
    }

    private Map<String, Object> buildDemoPayload() {
        String inquiryId = "nao-" + UUID.randomUUID();
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");
        String channel = props.getChannel() != null && !props.getChannel().isBlank()
                ? props.getChannel()
                : "DEFAULT";

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", inquiryId);
        payload.put("channel", channel);
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
                "addresses", java.util.List.of(Map.of(
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
                "exampleString", "NAO Java demo"
        ));
        payload.put("sharedContext", Map.of(
                "sourceClientId", props.getClientId() != null ? props.getClientId() : "",
                "sourceDeviceSessionId", deviceSessionId
        ));

        return payload;
    }
}
