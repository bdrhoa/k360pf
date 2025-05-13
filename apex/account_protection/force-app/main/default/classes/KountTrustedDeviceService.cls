


public with sharing class KountTrustedDeviceService {

    public class CreateRequest {
        @AuraEnabled public String clientId;
        @AuraEnabled public String sessionId;
        @AuraEnabled public String userId;
        @AuraEnabled public String trustState;
        @AuraEnabled public String friendlyName;
    }

    public class CreateResponse {
        public String clientId;
        public String sessionId;
        public String userId;
        public String deviceId;
        public String trustState;
        public String friendlyName;
        public String createdAt;
        public String lastUpdated;
    }

    public static CreateResponse createTrustedDevice(CreateRequest input) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:Kount_TrustedDevice/trusted-device');
        req.setMethod('POST');
        req.setHeader('Authorization', 'Bearer ' + KountJwtAuth.getAccessToken());
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(input));

        HttpResponse res = new Http().send(req);
        if (res.getStatusCode() != 200) {
            throw new CalloutException('Failed to create trusted device: ' + res.getBody());
        }

        return (CreateResponse) JSON.deserialize(res.getBody(), CreateResponse.class);
    }

    public class DeleteResponse {
        public String clientId;
        public String deviceId;
        public String userId;
    }

    public static DeleteResponse deleteTrustedDevice(String sessionId, String userId, String clientId) {
        HttpRequest req = new HttpRequest();
        String url = 'callout:Kount_TrustedDevice/trusted-device/sessions/' + sessionId + '/users/' + userId + '/clients/' + clientId;
        req.setEndpoint(url);
        req.setMethod('DELETE');
        req.setHeader('Authorization', 'Bearer ' + KountJwtAuth.getAccessToken());

        HttpResponse res = new Http().send(req);
        if (res.getStatusCode() != 200) {
            throw new CalloutException('Failed to delete trusted device: ' + res.getBody());
        }

        return (DeleteResponse) JSON.deserialize(res.getBody(), DeleteResponse.class);
    }
    // Async method to create trusted device
    @future(callout=true)
    public static void createTrustedDeviceAsync(String clientId, String sessionId, String userId, String trustState, String friendlyName) {
        CreateRequest input = new CreateRequest();
        input.clientId = clientId;
        input.sessionId = sessionId;
        input.userId = userId;
        input.trustState = trustState;
        input.friendlyName = friendlyName;
        createTrustedDevice(input);
    }

    // Async method to delete trusted device
    @future(callout=true)
    public static void deleteTrustedDeviceAsync(String sessionId, String userId, String clientId) {
        deleteTrustedDevice(sessionId, userId, clientId);
    }
}