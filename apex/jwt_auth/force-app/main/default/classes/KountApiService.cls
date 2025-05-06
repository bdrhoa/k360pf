public with sharing class KountApiService {
    private static final String BASE_URL = 'https://api-sandbox.kount.com';

    public static HttpResponse callLoginV2(Map<String, Object> payload) {
        return callKountApi('/login/v2', payload);
    }

    public static HttpResponse callChallengeOutcome(Map<String, Object> payload) {
        return callKountApi('/events/challengeOutcome', payload);
    }

    public static HttpResponse callTrustedDevice(Map<String, Object> payload) {
        return callKountApi('/trusted-device/v1', payload);
    }

    public static HttpResponse callNewAccountOpening(Map<String, Object> payload) {
        return callKountApi('/newaccountopening/v2', payload);
    }

    private static HttpResponse callKountApi(String endpoint, Map<String, Object> payload) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(BASE_URL + endpoint);
        req.setMethod('POST');
        req.setHeader('Authorization', 'Bearer ' + KountTokenManager.getToken());
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(payload));

        Http http = new Http();
        HttpResponse res = http.send(req);

        if (res.getStatusCode() >= 400) {
            throw new CalloutException('API call failed: ' + res.getBody());
        }
        return res;
    }
}