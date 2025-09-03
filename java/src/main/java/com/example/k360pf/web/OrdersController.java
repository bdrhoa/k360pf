package com.example.k360pf.web;

import com.example.k360pf.client.OrdersClient;
import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/demo")
public class OrdersController {
    private final OrdersClient orders;
    private final Kount360Properties props;

    public OrdersController(OrdersClient orders, Kount360Properties props) {
        this.orders = orders;
        this.props = props;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of("status", "ok", "time", Instant.now().toString());
    }

    @PostMapping("/orders")
    public ResponseEntity<?> sendDemoOrder() {
        Map<String, Object> order = new HashMap<>();
        order.put("merchantOrderId", "JAVA-" + UUID.randomUUID());
        order.put("channel", props.getChannel());
        order.put("deviceSessionId", UUID.randomUUID().toString());
        order.put("creationDateTime", Instant.now().toString());
        order.put("amount", Map.of("value", 1999, "currency", "USD"));
        order.put("account", Map.of(
                "firstName", "Jane",
                "lastName", "Doe",
                "email", "jane.doe@example.com"
        ));
        order.put("billingAddress", Map.of(
                "address1", "123 Main St",
                "city", "Boise",
                "region", "ID",
                "postalCode", "83702",
                "country", "US"
        ));
        order.put("payment", Map.of(
                "type", "CARD",
                "card", Map.of("last4", "4242", "brand", "VISA")
        ));

        Map<String, Object> resp = orders.postOrder(order);
        return ResponseEntity.ok(resp);
    }
}
