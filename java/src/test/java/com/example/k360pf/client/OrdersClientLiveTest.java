package com.example.k360pf.client;

import com.example.k360pf.config.Kount360Properties;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class OrdersClientLiveTest {

    @Test
    void postOrder_liveApi_returnsResponse() {
        String apiBaseUrl = "https://api-sandbox.kount.com";
        String authUrl = "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token";
        String clientId = System.getenv("KOUNT_CLIENT_ID");
        String apiKey = System.getenv("KOUNT_API_KEY");


        Assumptions.assumeTrue(authUrl != null && !authUrl.isBlank(),
                "KOUNT_AUTH_TOKEN_URL not set; skipping live Orders test");
        Assumptions.assumeTrue(apiBaseUrl != null && !apiBaseUrl.isBlank(),
                "KOUNT_API_BASE_URL not set; skipping live Orders test");
        Assumptions.assumeTrue(apiKey != null && !apiKey.isBlank(),
                "KOUNT_API_KEY not set; skipping live Orders test");

        Kount360Properties props = new Kount360Properties();
        props.setAuthTokenUrl(authUrl);
        props.setApiBaseUrl(apiBaseUrl);
        props.setApiKey(apiKey);

        AuthClient authClient = new AuthClient(props, org.springframework.web.reactive.function.client.WebClient.builder());
        OrdersClient ordersClient = new OrdersClient(authClient, props);

        Map<String, Object> payload = buildPayload();

        Map<String, Object> response = ordersClient.postOrder(payload);

        assertNotNull(response, "Orders API response should not be null");
        assertFalse(response.isEmpty(), "Orders API response should not be empty");

        System.out.println("Live Orders response:");
        System.out.println(response);
    }

    private Map<String, Object> buildPayload() {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("merchantOrderId", "1774044330");
        payload.put("channel", "DEFAULT");
        payload.put("deviceSessionId", "Gja7iow3IPKjUZJeV2zVKMcAEPnSeZol");
        payload.put("creationDateTime", "2026-03-20T22:03:30Z");
        payload.put("userIp", "641b:e60b:16b0:f329:db24:9b7a:48bc:72e3");

        payload.put("account", Map.of(
                "id", "554",
                "type", "circuit",
                "creationDateTime", "2026-03-20T22:05:30.204Z",
                "username", "Dexter43",
                "accountIsActive", false
        ));

        payload.put("items", List.of(
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

        payload.put("fulfillment", List.of(
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

        payload.put("transactions", List.of(
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
                        Map.entry("merchantTransactionId", "b7e2ca00-023b-460b-8cb2-b2d13ba6d2b4"),
                        Map.entry("items", List.of(
                                Map.of("id", "60", "quantity", 79866928)
                        ))
                )
        ));

        payload.put("promotions", List.of(
                Map.of(
                        "id", "b6955f98-1073-4308-80a8-6ce7751d0e3c",
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

        payload.put("loyalty", Map.of(
                "id", "794ff0d2-5323-4a04-a412-71baafb89e01",
                "description", "Tolero balbus victoria desidero aspernatur sui torqueo templum tot vae.",
                "credit", Map.of(
                        "creditType", "matrix",
                        "amount", 931,
                        "currency", "QAR"
                )
        ));

        payload.put("customFields", Map.of(
                "keyNumber", "67",
                "keyBoolean", false,
                "keyString", "sensor",
                "keyDate", "2026-03-24T01:39:19.949Z"
        ));

        return payload;
    }
}