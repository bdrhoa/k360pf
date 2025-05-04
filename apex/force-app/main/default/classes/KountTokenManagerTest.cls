@isTest
private class KountTokenManagerTest {

    @testSetup
    static void setup() {
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            AccessToken__c = 'initialToken',
            ExpirationEpoch__c = DateTime.now().addMinutes(10).getTime() / 1000,
            ApiKey__c = 'testApiKey'
        );
        insert config;
    }

    @isTest
    static void testGetToken_ValidToken() {
        String token = KountTokenManager.getToken();
        System.assertEquals('initialToken', token);
    }

    @isTest
    static void testGetToken_ExpiredToken() {
        Test.setMock(HttpCalloutMock.class, new KountJwtAuthMock());
        KountAuthConfig__c config = [SELECT Id, ExpirationEpoch__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
        config.ExpirationEpoch__c = DateTime.now().addMinutes(-10).getTime() / 1000;
        update config;

        Test.startTest();
        String token = KountTokenManager.getToken();
        Test.stopTest();

        System.assertNotEquals('initialToken', token, 'Should have refreshed the token');
    } 

    @isTest
    static void testRefreshToken_InjectSetting() {
        Test.setMock(HttpCalloutMock.class, new KountJwtAuthMock());
        KountAuthConfig__c injected = new KountAuthConfig__c(
            Name = 'Injected',
            AccessToken__c = 'oldToken',
            ExpirationEpoch__c = DateTime.now().addMinutes(-5).getTime() / 1000,
            ApiKey__c = 'testKey'
        );
        
        insert injected;

        Test.startTest();
        KountTokenManager.refreshToken(injected);
        Test.stopTest();

        injected = [SELECT AccessToken__c FROM KountAuthConfig__c WHERE Name = 'Injected' LIMIT 1];
        System.assertNotEquals('oldToken', injected.AccessToken__c);
    }

    @isTest
    static void testIsExpiredLogic() {
        KountAuthConfig__c config = new KountAuthConfig__c(Name = 'TestCheck');

        // Null expiration
        System.assertEquals(true, KountTokenManager.isExpired(config));

        // Future expiration
        config.ExpirationEpoch__c = DateTime.now().addMinutes(10).getTime() / 1000;
        System.assertEquals(false, KountTokenManager.isExpired(config));

        // Past expiration
        config.ExpirationEpoch__c = DateTime.now().addMinutes(-10).getTime() / 1000;
        System.assertEquals(true, KountTokenManager.isExpired(config));
    }
}
