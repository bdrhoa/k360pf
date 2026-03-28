package com.example.k360pf.web;

import com.example.k360pf.security.SignatureVerifier;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.util.StreamUtils;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletRequest;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

@RestController
@RequestMapping("/webhooks/kount360")
public class WebhookController {
    private static final Logger log = LoggerFactory.getLogger(WebhookController.class);

    private final SignatureVerifier verifier;
    private final ObjectMapper objectMapper;

    public WebhookController(SignatureVerifier verifier, ObjectMapper objectMapper) {
        this.verifier = verifier;
        this.objectMapper = objectMapper;
    }

    @PostMapping
    public ResponseEntity<?> receive(HttpServletRequest request,
                                     @RequestHeader(value = "X-Event-Timestamp", required = false) String timestampHeader,
                                     @RequestHeader(value = "X-Event-Signature", required = false) String signatureHeader) throws Exception {
        if (timestampHeader == null || timestampHeader.isBlank()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Missing X-Event-Timestamp header");
        }
        if (signatureHeader == null || signatureHeader.isBlank()) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Missing X-Event-Signature header");
        }

        byte[] bodyBytes = StreamUtils.copyToByteArray(request.getInputStream());
        String body = new String(bodyBytes, StandardCharsets.UTF_8);

        log.info("Raw request body: {}", body);
        log.info("X-Event-Timestamp: {}", timestampHeader);
        log.info("X-Event-Signature: {}", signatureHeader);

        if (body.isBlank()) {
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body("Empty request body");
        }

        try {
            byte[] timestampBytes = timestampHeader.getBytes(StandardCharsets.UTF_8);
            byte[] digest = new byte[timestampBytes.length + bodyBytes.length];
            System.arraycopy(timestampBytes, 0, digest, 0, timestampBytes.length);
            System.arraycopy(bodyBytes, 0, digest, timestampBytes.length, bodyBytes.length);
            String digestBase64 = Base64.getEncoder().encodeToString(digest);
            log.info("Digest base64 for test reconstruction: {}", digestBase64);

            verifier.verifySignature(signatureHeader, timestampHeader, bodyBytes);
        } catch (IllegalArgumentException ex) {
            log.error("Signature verification error: {}", ex.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(ex.getMessage());
        } catch (IllegalStateException ex) {
            log.error("Public key error: {}", ex.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(ex.getMessage());
        }

        try {
            JsonNode payload = objectMapper.readTree(body);
            JsonNode newValueNode = payload.get("newValue");
            String newValue = newValueNode != null && !newValueNode.isNull() ? newValueNode.asText() : null;

            if ("DECLINE".equals(newValue)) {
                log.info("Simulated order cancellation");
            } else if ("APPROVE".equals(newValue)) {
                log.info("Simulated order processing");
            } else {
                log.error("Unexpected newValue: {}", newValue);
            }
        } catch (JsonProcessingException ex) {
            log.error("Invalid JSON payload: {}", ex.getMessage());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("Invalid JSON payload");
        }

        return ResponseEntity.ok(Map.of("status", "ok"));
    }
}
