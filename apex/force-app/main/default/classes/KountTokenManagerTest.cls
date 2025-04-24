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

        delete [SELECT Id FROM KountAuthSetting__c WHERE Name = 'Default' LIMIT 1];

        Test.startTest();
        KountTokenManager.refreshToken();
        String token = KountTokenManager.getToken();
        Test.stopTest();

        System.assertEquals('test_token', token);
    }

    @IsTest
    static void testScheduler() {
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());
        Test.startTest();
        String jobId = System.schedule('Test Refresh Job', '0 0 0 1 1 ? 2099', new KountTokenRefresher());
        Test.stopTest();
        System.assertNotEquals(null, jobId);
    }
}