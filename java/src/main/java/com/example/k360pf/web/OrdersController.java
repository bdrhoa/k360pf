package com.example.k360pf.web;

import com.example.k360pf.client.OrdersClient;
import com.example.k360pf.config.Kount360Properties;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.List;

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
        Map<String, Object> order = buildDemoOrderPayload();
        Map<String, Object> resp = orders.postOrder(order);
        return ResponseEntity.ok(resp);
    }
    private Map<String, Object> buildDemoOrderPayload() {
        String now = Instant.now().toString();

        Map<String, Object> order = new java.util.LinkedHashMap<>();
        order.put("merchantOrderId", String.valueOf(System.currentTimeMillis()));
        order.put("channel", props.getChannel() != null && !props.getChannel().isBlank() ? props.getChannel() : "DEFAULT");
        order.put("deviceSessionId", UUID.randomUUID().toString().replace("-", ""));
        order.put("creationDateTime", now);
        order.put("userIp", "641b:e60b:16b0:f329:db24:9b7a:48bc:72e3");

        order.put("account", Map.of(
                "id", "554",
                "type", "circuit",
                "creationDateTime", now,
                "username", "Dexter43",
                "accountIsActive", false
        ));

        order.put("items", List.of(
                Map.ofEntries(
                        Map.entry("price", 544),
                        Map.entry("description", "Crepusculum toties pectus aggredior harum adulatio cado."),
                        Map.entry("name", "Sleek Granite Towels"),
                        Map.entry("quantity", 9),
                        Map.entry("category", "Health"),
                        Map.entry("subCategory", "monitor"),
                        Map.entry("isDigital", false),
                        Map.entry("sku", "914"),
                        Map.entry("upc", "304"),
                        Map.entry("brand", "driver"),
                        Map.entry("url", "https://prudent-barge.biz/"),
                        Map.entry("imageUrl", "https://picsum.photos/seed/sgMI4Cvo/1972/1881"),
                        Map.entry("physicalAttributes", Map.of(
                                "color", "white",
                                "size", "bandwidth",
                                "weight", "713",
                                "height", "109",
                                "width", "716",
                                "depth", "964"
                        )),
                        Map.entry("descriptors", List.of("bandwidth", "sensor")),
                        Map.entry("id", "504"),
                        Map.entry("isService", true)
                )
        ));

        order.put("fulfillment", List.of(
                Map.ofEntries(
                        Map.entry("type", "SHIPPED"),
                        Map.entry("shipping", Map.of(
                                "amount", 366,
                                "provider", "Kessler - Labadie",
                                "trackingNumber", "92bf50dd-c632-42ce-84aa-4a111db19c0d",
                                "method", "STANDARD"
                        )),
                        Map.entry("recipientPerson", Map.ofEntries(
                                Map.entry("name", Map.of(
                                        "first", "Albert",
                                        "preferred", "Karl",
                                        "family", "Schimmel",
                                        "middle", "microchip",
                                        "prefix", "Miss",
                                        "suffix", "III"
                                )),
                                Map.entry("phoneNumber", "(705) 961-8982 x8669"),
                                Map.entry("emailAddress", "Waino.Murray@yahoo.com"),
                                Map.entry("address", Map.of(
                                        "line1", "5700 Yonge St, Suite 1700",
                                        "city", "Toronto",
                                        "region", "ON",
                                        "countryCode", "CA",
                                        "postalCode", "M2M 4K2"
                                )),
                                Map.entry("dateOfBirth", "2025-04-11T19:13:55.310Z")
                        )),
                        Map.entry("items", List.of(
                                Map.of("id", "26", "quantity", 58330778)
                        )),
                        Map.entry("status", "FULFILLED"),
                        Map.entry("accessUrl", "https://insidious-lay.org/"),
                        Map.entry("store", Map.of(
                                "id", "836",
                                "name", "Bartoletti - Bartoletti",
                                "address", Map.of(
                                        "line1", "5700 Yonge St, Suite 1700",
                                        "city", "Toronto",
                                        "region", "ON",
                                        "countryCode", "CA",
                                        "postalCode", "M2M 4K2"
                                )
                        )),
                        Map.entry("merchantFulfillmentId", "26ab50eb-81d7-4dd9-a132-9b4c3e183fb2"),
                        Map.entry("digitalDownloaded", true),
                        Map.entry("downloadDeviceIp", "6c38:b69b:b691:6da1:8434:fca6:0bc4:ba0e")
                )
        ));

        order.put("transactions", List.of(
                Map.ofEntries(
                        Map.entry("processor", "monitor"),
                        Map.entry("processorMerchantId", "PK40YMKA5004800740030268"),
                        Map.entry("payment", Map.of(
                                "type", "CARD",
                                "paymentToken", "411111WMS5YA6FUZA1KC",
                                "bin", "411111",
                                "last4", "1111"
                        )),
                        Map.entry("subtotal", 4896),
                        Map.entry("orderTotal", 4896),
                        Map.entry("currency", "USD"),
                        Map.entry("tax", Map.of(
                                "isTaxable", true,
                                "taxableCountryCode", "US",
                                "taxAmount", 29376
                        )),
                        Map.entry("billedPerson", Map.ofEntries(
                                Map.entry("name", Map.of(
                                        "first", "Branson",
                                        "preferred", "Albert",
                                        "family", "Bergstrom",
                                        "middle", "interface",
                                        "prefix", "Mr.",
                                        "suffix", "IV"
                                )),
                                Map.entry("phoneNumber", "797.718.8113 x6706"),
                                Map.entry("emailAddress", "Monroe_Lebsack@yahoo.com"),
                                Map.entry("address", Map.of(
                                        "line1", "5700 Yonge St, Suite 1700",
                                        "city", "Toronto",
                                        "region", "ON",
                                        "countryCode", "CA",
                                        "postalCode", "M2M 4K2"
                                )),
                                Map.entry("dateOfBirth", "2025-06-22T05:21:42.092Z")
                        )),
                        Map.entry("merchantTransactionId", UUID.randomUUID().toString()),
                        Map.entry("items", List.of(
                                Map.of("id", "60", "quantity", 79866928)
                        ))
                )
        ));

        order.put("promotions", List.of(
                Map.of(
                        "id", UUID.randomUUID().toString(),
                        "description", "Tolero concido carus aeger eaque deripio capitulus.",
                        "status", "capacitor",
                        "statusReason", "protocol",
                        "discount", Map.of(
                                "percentage", "633",
                                "amount", 472,
                                "currency", "LYD"
                        ),
                        "credit", Map.of(
                                "creditType", "application",
                                "amount", 215,
                                "currency", "BDT"
                        )
                )
        ));

        order.put("loyalty", Map.of(
                "id", UUID.randomUUID().toString(),
                "description", "Tolero balbus victoria desidero aspernatur sui torqueo templum tot vae.",
                "credit", Map.of(
                        "creditType", "matrix",
                        "amount", 931,
                        "currency", "QAR"
                )
        ));

        order.put("customFields", Map.of(
                "keyNumber", "67",
                "keyBoolean", false,
                "keyString", "sensor",
                "keyDate", now
        ));

        return order;
    }
}
