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
    @isTest
    static void testGetExpirationEpochFromJwt() {
        String jwt = 'eyJraWQiOiJPdTRzeVUxbHJUZDJpeWJhN0ZTR3c2RlF1WG10cXRtVDVVX2lvSXR5X1Q0IiwiYWxnIjoiUlMyNTYifQ.eyJ2ZXIiOjEsImp0aSI6IkFULnlJNUFnOU9WRW9sc241dWoxZ3Bjc3hPT2FlNlprU2M4TkU5RXpVamZncTQiLCJpc3MiOiJodHRwczovL2xvZ2luLmtvdW50LmNvbS9vYXV0aDIvYXVzZHBwa3VqekNQUXVJclkzNTciLCJhdWQiOiJrMV9zYW5kYm94MTNfaW50ZWdyYXRpb25fYXBpX2F1dGhfc2VydmVyIiwic3ViIjoiMG9hMWJjNXgxcmJrd3ZlM3kzNTgiLCJpYXQiOjE3NDYzMzE3MDgsImV4cCI6MTc0NjMzMjkwOCwiY2lkIjoiMG9hMWJjNXgxcmJrd3ZlM3kzNTgiLCJzY3AiOlsiazFfaW50ZWdyYXRpb25fYXBpIl0sImVudGl0bGVtZW50cyI6WyJwYXltZW50c19mcmF1ZF9tYW51YWxfcmV2aWV3IiwiYXBfbG9naW4iLCJiYXNlIiwiYXBfbmV3X2FjY291bnRfb3BlbmluZyIsInBheW1lbnRzX2ZyYXVkIl0sIm9yZ19pZCI6ImNzNGljdWhyYWdkODJtY3RldXQwIiwiY2xpZW50X2lkIjoiOTI4NzM3Mzc5Nzk5MDkzIn0.Wy0hCBxhBJADdGp5AuCLlNYP--3lVaOa87WSm3eaiEiLNAlj_sF85CSTB6w-ufIX9hVMWFA6iCsTFXlweAgV-A7aPcO2pBeBGrBCNrfRqMFLFvKJ--sEH0FXuqk26nNVTmPCAEbrOBf6RC0vBh4NPPY8J4TWm-_X3dB9pBYvPxjhkShT0R4bkvrzCcPOwcYpw6KSCUd1TCjXusfTgHSz-93_wxnWTyLs8ouAJtuYl4WhhX33YpHTsk8P6EjenMEYGPfrSPEdZFraEen_WoMTzG6xrN-FhowFA3xzRmc5_aLlbST-ENp5sI9WNurbKGsDhMO5kVGUOYQRgWjghqMDQA';
        Long expectedEpoch = 1746332908;
        Long actualEpoch = KountTokenManager.getExpirationEpochFromJwt(jwt);
        System.assertEquals(expectedEpoch, actualEpoch, 'Should parse exp field from JWT');
    }
}
