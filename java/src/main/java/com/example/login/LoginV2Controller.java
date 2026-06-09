package com.example.login;

import com.example.k360pf.client.KountDecisionResponse;
import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/demo/login")
public class LoginV2Controller {
    private final LoginV2Client loginClient;
    private final Kount360Properties props;

    public LoginV2Controller(LoginV2Client loginClient, Kount360Properties props) {
        this.loginClient = loginClient;
        this.props = props;
    }

    @PostMapping
    public ResponseEntity<?> sendDemoLogin() {
        Map<String, Object> payload = buildDemoPayload();
        KountDecisionResponse response = loginClient.postLogin(payload);
        return ResponseEntity.ok(response);
    }

    private Map<String, Object> buildDemoPayload() {
        String inquiryId = "login-" + UUID.randomUUID();
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");
        String channel = props.getChannel() != null && !props.getChannel().isBlank()
                ? props.getChannel()
                : "DEFAULT";

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", inquiryId);
        payload.put("channel", channel);
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
                "creationDateTime", OffsetDateTime.of(2024, 1, 1, 12, 12, 12, 0, ZoneOffset.UTC)
                        .format(DateTimeFormatter.ISO_INSTANT),
                "username", "meoyyd8za8jdmwfm",
                "userPassword", "38401eb46f8fbb74c1846a5f47f68d83a9bef126b1d4143f886cd464323cdaab",
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
                "exampleString", "Login Java demo"
        ));

        return payload;
    }
}
