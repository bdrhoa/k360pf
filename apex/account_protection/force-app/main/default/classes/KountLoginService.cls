public with sharing class KountLoginService {

    private static final String LOGIN_DECISION_URL = 'https://api-sandbox.kount.com/login/v2';
    private static final String FAILED_ATTEMPT_URL = 'https://api-sandbox.kount.com/events/failed-attempt';

    public class LoginRequest {
        public String inquiryId;
        public String channel;
        public String deviceSessionId;
        public String userIp;
        public String loginUrl;
        public Person person;
        public Account account;
        public Strategy strategy;
    }

    public class Person {
        public Name name;
        public String emailAddress;
        public String phoneNumber;
        public List<Address> addresses;
    }

    public class Name {
        public String first;
        public String last;
        public String preferred;
    }

    public class Address {
        public String line1;
        public String line2;
        public String city;
        public String region;
        public String postalCode;
        public String countryCode;
        public String addressType;
    }

    public class Account {
        public String id;
        public String type;
        public String creationDateTime;
        public String username;
        public String userPassword;
        public Boolean accountIsActive;
    }

    public class Strategy {
        public String mfaTemplateName;
    }

    public static HttpResponse sendLoginRequest(LoginRequest request, KountAuthConfig__c config) {
        String token = KountTokenManager.getToken(config);
        HttpRequest req = new HttpRequest();
        req.setEndpoint(LOGIN_DECISION_URL);
        req.setMethod('POST');
        req.setHeader('Authorization', 'Bearer ' + token);
        req.setHeader('Content-Type', 'application/json');
        req.setBody(JSON.serialize(request));

        Http http = new Http();
        return http.send(req);
    }

    public static HttpResponse sendLoginRequest(LoginRequest request) {
       return sendLoginRequest(request, null);
    }

    public class FailedAttemptEvent {
        public String clientId;
        public String sessionId;
        public String userId;
        public String username;
    }

    public static HttpResponse sendFailedLogin(FailedAttemptEvent event, KountAuthConfig__c config) {
        String token = KountTokenManager.getToken(config);
        HttpRequest req = new HttpRequest();
        req.setEndpoint(FAILED_ATTEMPT_URL);
        req.setMethod('POST');
        req.setHeader('Authorization', 'Bearer ' + token);
        req.setHeader('Content-Type', 'application/json');

        Map<String, Object> payload = new Map<String, Object>{
            'failedAttempt' => event
        };

        req.setBody(JSON.serialize(payload));

        Http http = new Http();
        return http.send(req);
    }

    public static HttpResponse sendFailedLogin(FailedAttemptEvent event) {
        return sendFailedLogin(event, null);
    }
} 

// ChallengeOutcome support would be in a shared service like:
// KountChallengeOutcomeService.sendChallengeOutcome(...)
