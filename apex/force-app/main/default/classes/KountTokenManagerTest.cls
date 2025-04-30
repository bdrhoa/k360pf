@IsTest
private class KountTokenManagerTest {
    class MockHttpResponseGenerator implements HttpCalloutMock {
        public HTTPResponse respond(HTTPRequest req) {
            HttpResponse res = new HttpResponse();
            res.setHeader('Content-Type', 'application/json');
            res.setBody('{"access_token":"test_token","expires_in":3600}');
            res.setStatusCode(200);
            return res;
        }
    }

    @IsTest
    static void testTokenRefreshAndGetToken() {
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        KountAuthSetting__c setting = KountAuthSetting__c.getInstance();
        setting.AccessToken__c = null;
        setting.ExpirationEpoch__c = 0;
        upsert setting;

        Test.startTest();
        KountTokenManager.refreshToken(setting);
        String token = KountTokenManager.getToken(setting);
        Test.stopTest();

        System.assertEquals('test_token', token);
    }

    @IsTest
    static void testScheduler() {
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        KountAuthSetting__c setting = KountAuthSetting__c.getInstance();
        setting.AccessToken__c = null;
        setting.ExpirationEpoch__c = 0;
        upsert setting;
        KountTokenRefresher.testSetting = setting;

        Test.startTest();
        String jobId = System.schedule('Test Refresh Job', '0 0 0 1 1 ? 2099', new KountTokenRefresher());
        Test.stopTest();
        System.assertNotEquals(null, jobId);
    }
}