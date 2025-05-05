@isTest
private class KountLoginServiceTest {

    @isTest
    static void testSendLoginRequest() {
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            AccessToken__c = 'dummy.jwt.token',
            ExpirationEpoch__c = 9999999999L
        );
        insert config;

        Test.startTest();

        // Construct a minimal valid login request
        KountLoginService.LoginRequest request = new KountLoginService.LoginRequest();
        request.inquiryId = 'inq123';
        request.channel = 'ACME_WEB';
        request.deviceSessionId = 'abc123';
        request.userIp = '192.168.1.1';
        request.loginUrl = 'https://example.com/login';

        request.person = new KountLoginService.Person();
        request.person.name = new KountLoginService.Name();
        request.person.name.first = 'Jane';
        request.person.name.last = 'Doe';
        request.person.name.preferred = 'Janie';
        request.person.emailAddress = 'jane@example.com';
        request.person.phoneNumber = '+15555550123';
        request.person.addresses = new List<KountLoginService.Address>{
            new KountLoginService.Address()
        };

        request.account = new KountLoginService.Account();
        request.account.id = 'acct123';
        request.account.type = 'STANDARD';
        request.account.creationDateTime = '2024-01-01T12:12:12.000Z';
        request.account.username = 'jane_doe';
        request.account.userPassword = 'hashedpassword';
        request.account.accountIsActive = true;

        request.strategy = new KountLoginService.Strategy();
        request.strategy.mfaTemplateName = 'default_template';

        // Mock the callout
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        HttpResponse response = KountLoginService.sendLoginRequest(request, config);
        System.assertEquals(200, response.getStatusCode());

        Test.stopTest();
    }

    @isTest
    static void testSendFailedLogin() {
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            AccessToken__c = 'dummy.jwt.token',
            ExpirationEpoch__c = 9999999999L
        );
        insert config;

        Test.startTest();

        KountLoginService.FailedAttemptEvent event = new KountLoginService.FailedAttemptEvent();
        event.clientId = '900900';
        event.sessionId = 'sess123';
        event.userId = 'user123';
        event.username = 'jane_doe';

        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        HttpResponse response = KountLoginService.sendFailedLogin(event, config);
        System.assertEquals(200, response.getStatusCode());

        Test.stopTest();
    }
}