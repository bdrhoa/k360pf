package com.example.events;

import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/demo/events")
public class KountEventsController {
    private final KountEventsClient eventsClient;
    private final Kount360Properties props;

    public KountEventsController(KountEventsClient eventsClient, Kount360Properties props) {
        this.eventsClient = eventsClient;
        this.props = props;
    }

    @PostMapping("/failed-attempt")
    public ResponseEntity<?> sendDemoFailedAttempt() {
        return ResponseEntity.ok(eventsClient.postFailedAttempt(buildFailedAttemptPayload()));
    }

    @PostMapping("/challenge-outcome")
    public ResponseEntity<?> sendDemoChallengeOutcome(@RequestBody(required = false) Map<String, Object> overrides) {
        Map<String, Object> payload = buildChallengeOutcomePayload(overrides);
        return ResponseEntity.ok(eventsClient.postChallengeOutcome(payload));
    }

    private Map<String, Object> buildFailedAttemptPayload() {
        String deviceSessionId = UUID.randomUUID().toString().replace("-", "");
        String channel = props.getChannel() != null && !props.getChannel().isBlank()
                ? props.getChannel()
                : "DEFAULT";

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "failed-attempt-" + UUID.randomUUID());
        payload.put("channel", channel);
        payload.put("deviceSessionId", deviceSessionId);
        payload.put("userIp", "192.168.0.1");
        payload.put("loginUrl", "https://www.example.com/login");
        payload.put("person", Map.of(
                "emailAddress", "john.doe@example.com",
                "phoneNumber", "+12081234567",
                "name", Map.of(
                        "first", "John",
                        "last", "Doe"
                )
        ));
        payload.put("account", Map.of(
                "id", "meoyyd8za8jdmwfm",
                "type", "VIP",
                "username", "meoyyd8za8jdmwfm"
        ));
        return payload;
    }

    private Map<String, Object> buildChallengeOutcomePayload(Map<String, Object> overrides) {
        Instant sent = Instant.now().minus(1, ChronoUnit.MINUTES).truncatedTo(ChronoUnit.MILLIS);
        Instant completed = Instant.now().truncatedTo(ChronoUnit.MILLIS);

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("inquiryId", "challenge-outcome-" + UUID.randomUUID());
        payload.put("deviceSessionId", UUID.randomUUID().toString().replace("-", ""));
        payload.put("decisionCorrelationId", UUID.randomUUID().toString());
        payload.put("challengeType", "Captcha");
        payload.put("challengeStatus", "Success");
        payload.put("sentTimestamp", sent.toString());
        payload.put("completedTimestamp", completed.toString());

        if (overrides != null) {
            payload.putAll(overrides);
        }

        return payload;
    }
}
