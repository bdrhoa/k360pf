package com.example.k360pf.client;

import java.util.Collections;
import java.util.Map;

public class KountDecisionResponse {
    private final Map<String, Object> body;
    private final String decision;
    private final String correlationId;

    public KountDecisionResponse(Map<String, Object> body, String correlationId) {
        this.body = body != null ? body : Collections.emptyMap();
        this.decision = extractDecision(this.body);
        this.correlationId = correlationId;
    }

    public Map<String, Object> getBody() {
        return body;
    }

    public String getDecision() {
        return decision;
    }

    public String getCorrelationId() {
        return correlationId;
    }

    public boolean isChallenge() {
        return "CHALLENGE".equalsIgnoreCase(decision);
    }

    public boolean isAllow() {
        return "ALLOW".equalsIgnoreCase(decision);
    }

    public boolean isBlock() {
        return "BLOCK".equalsIgnoreCase(decision);
    }

    private static String extractDecision(Map<String, Object> body) {
        Object value = body.get("decision");
        return value != null ? String.valueOf(value) : null;
    }
}
