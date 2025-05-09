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
        HttpResponse res = http.send(req);
        System.debug('Kount Login Response Status: ' + res.getStatus());
        System.debug('Kount Login Response Body: ' + res.getBody());
        return res;
    }

    public static HttpResponse sendLoginRequest(LoginRequest request) {
       return sendLoginRequest(request, null);
    }


    public class FailedAttemptEvent {
        public String inquiryId;
        public String channel;
        public String deviceSessionId;
        public String userIp;
        public String loginUrl;
        public Person person;
        public Account account;
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

        String requestBody = JSON.serialize(payload);
        req.setBody(requestBody);
        
        // Add detailed logging
        System.debug('Kount Failed Login Request Details:');
        System.debug('Endpoint: ' + FAILED_ATTEMPT_URL);
        System.debug('Request Body: ' + requestBody);
        System.debug('Event Details:');
        System.debug('  inquiryId: ' + event.inquiryId);
        System.debug('  channel: ' + event.channel);
        System.debug('  deviceSessionId: ' + event.deviceSessionId);
        System.debug('  userIp: ' + event.userIp);
        System.debug('  loginUrl: ' + event.loginUrl);
        System.debug('  emailAddress: ' + event.person.emailAddress);
        System.debug('  phoneNumber: ' + event.person.phoneNumber);
        System.debug('  accountId: ' + event.account.id);
        System.debug('  accountType: ' + event.account.type);
        System.debug('  accountCreationDateTime: ' + event.account.creationDateTime);
        System.debug('  accountUsername: ' + event.account.username);
        System.debug('  accountUserPassword: ' + event.account.userPassword);
        System.debug('  accountIsActive: ' + event.account.accountIsActive);

        Http http = new Http();
        HttpResponse res = http.send(req);
        System.debug('Kount Failed Login Response Status: ' + res.getStatus());
        System.debug('Kount Failed Login Response Body: ' + res.getBody());
        return res;
    }

    public static HttpResponse sendFailedLogin(FailedAttemptEvent event) {
        return sendFailedLogin(event, null);
    }

    @future(callout=true)
    public static void sendAsyncFailedLogin(
        String inquiryId,
        String channel,
        String deviceSessionId,
        String userIp,
        String loginUrl,
        String emailAddress,
        String phoneNumber,
        String userId,
        String username,
        String accountType,
        String creationDateTime,
        String userPassword,
        Boolean accountIsActive
    ) {
        FailedAttemptEvent event = new FailedAttemptEvent();
        event.inquiryId = inquiryId;
        event.channel = channel;
        event.deviceSessionId = deviceSessionId;
        event.userIp = userIp;
        event.loginUrl = loginUrl;
        
        // Set up person
        event.person = new Person();
        event.person.emailAddress = emailAddress;
        event.person.phoneNumber = phoneNumber;
        
        // Set up account
        event.account = new Account();
        event.account.id = userId;
        event.account.username = username;
        event.account.type = accountType;
        event.account.creationDateTime = creationDateTime;
        event.account.userPassword = userPassword;
        event.account.accountIsActive = accountIsActive;
        
        sendFailedLogin(event);
    }

    public static void ensureTokenReady() {
        KountTokenManager.getToken();
    }

} 

// ChallengeOutcome support would be in a shared service like:
// KountChallengeOutcomeService.sendChallengeOutcome(...)

