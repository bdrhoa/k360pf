package com.example.k360pf.web;

import com.example.k360pf.config.Kount360Properties;
import com.example.k360pf.security.SignatureVerifier;
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
import java.util.Map;

@RestController
@RequestMapping("/webhooks/kount360")
public class WebhookController {
    private static final Logger log = LoggerFactory.getLogger(WebhookController.class);
    private final SignatureVerifier verifier;
    private final Kount360Properties props;

    public WebhookController(SignatureVerifier verifier, Kount360Properties props) {
        this.verifier = verifier;
        this.props = props;
    }

    @PostMapping
    public ResponseEntity<?> receive(HttpServletRequest request,
                                     @RequestHeader(value = "X-Kount-Signature", required = false) String xSig,
                                     @RequestHeader(value = "Signature", required = false) String sigFallback) throws Exception {
        byte[] body = StreamUtils.copyToByteArray(request.getInputStream());
        String bodyStr = new String(body, StandardCharsets.UTF_8);
        String sig = xSig != null ? xSig : sigFallback;
        if (sig == null || sig.isEmpty()) {
            log.warn("Missing signature header ({} or Signature)", props.getSignatureHeader());
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "missing signature header"));
        }
        boolean ok = verifier.verify(body, sig);
        if (!ok) {
            log.warn("Invalid webhook signature");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("status", "invalid-signature"));
        }
        log.info("Webhook verified: {}", bodyStr);
        return ResponseEntity.ok(Map.of("status", "ok"));
    }
}
