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
        event.inquiryId = 'inq123';
        event.channel = 'WEB';
        event.deviceSessionId = 'dev123';
        event.userIp = '192.168.1.1';
        event.loginUrl = 'https://example.com/login';
        
        // Set up person
        event.person = new KountLoginService.Person();
        event.person.emailAddress = 'test@example.com';
        event.person.phoneNumber = '+15555550123';
        
        // Set up account
        event.account = new KountLoginService.Account();
        event.account.id = 'user123';
        event.account.username = 'jane_doe';
        event.account.type = 'STANDARD';
        event.account.creationDateTime = '2024-01-01T12:12:12.000Z';
        event.account.userPassword = 'hashedpassword';
        event.account.accountIsActive = true;

        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        HttpResponse response = KountLoginService.sendFailedLogin(event, config);
        System.assertEquals(200, response.getStatusCode());

        Test.stopTest();
    }

    @isTest
    static void testSendAsyncFailedLogin() {
        // Set up the auth config first
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            AccessToken__c = 'dummy.jwt.token',
            ExpirationEpoch__c = 9999999999L
        );
        insert config;

        Test.startTest();

        // Set up test data
        String inquiryId = 'inq_' + String.valueOf(Datetime.now().getTime());
        String channel = 'WEB';
        String deviceSessionId = 'dev_' + String.valueOf(Datetime.now().getTime());
        String userIp = '192.168.1.1';
        String loginUrl = 'https://example.com/login';
        String emailAddress = 'test@example.com';
        String phoneNumber = '+15555550123';
        String userId = 'user123';
        String username = 'jane_doe';
        String accountType = 'STANDARD';
        String creationDateTime = Datetime.now().format('yyyy-MM-dd\'T\'HH:mm:ss.SSS\'Z\'');
        String userPassword = 'hashedpassword';
        Boolean accountIsActive = true;

        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        // Call the async method
        KountLoginService.sendAsyncFailedLogin(
            inquiryId,
            channel,
            deviceSessionId,
            userIp,
            loginUrl,
            emailAddress,
            phoneNumber,
            userId,
            username,
            accountType,
            creationDateTime,
            userPassword,
            accountIsActive
        );

        Test.stopTest();
    }
}