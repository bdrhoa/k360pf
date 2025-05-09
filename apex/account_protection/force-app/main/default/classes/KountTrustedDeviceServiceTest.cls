@isTest
private class KountTrustedDeviceServiceTest {

    class MockHttpResponseGenerator implements HttpCalloutMock {
        public HTTPResponse respond(HTTPRequest req) {
            HttpResponse res = new HttpResponse();
            res.setHeader('Content-Type', 'application/json');

            // Handle JWT auth callout
            if (req.getEndpoint().contains('oauth2')) {
                res.setStatusCode(200);
                res.setBody('{"access_token": "eyJraWQiOiJPdTRzeVUxbHJUZDJpeWJhN0ZTR3c2RlF1WG10cXRtVDVVX2lvSXR5X1Q0IiwiYWxnIjoiUlMyNTYifQ.eyJ2ZXIiOjEsImp0aSI6IkFULnlJNUFnOU9WRW9sc241dWoxZ3Bjc3hPT2FlNlprU2M4TkU5RXpVamZncTQiLCJpc3MiOiJodHRwczovL2xvZ2luLmtvdW50LmNvbS9vYXV0aDIvYXVzZHBwa3VqekNQUXVJclkzNTciLCJhdWQiOiJrMV9zYW5kYm94MTNfaW50ZWdyYXRpb25fYXBpX2F1dGhfc2VydmVyIiwic3ViIjoiMG9hMWJjNXgxcmJrd3ZlM3kzNTgiLCJpYXQiOjE3NDYzMzE3MDgsImV4cCI6MTc0NjMzMjkwOCwiY2lkIjoiMG9hMWJjNXgxcmJrd3ZlM3kzNTgiLCJzY3AiOlsiazFfaW50ZWdyYXRpb25fYXBpIl0sImVudGl0bGVtZW50cyI6WyJwYXltZW50c19mcmF1ZF9tYW51YWxfcmV2aWV3IiwiYXBfbG9naW4iLCJiYXNlIiwiYXBfbmV3X2FjY291bnRfb3BlbmluZyIsInBheW1lbnRzX2ZyYXVkIl0sIm9yZ19pZCI6ImNzNGljdWhyYWdkODJtY3RldXQwIiwiY2xpZW50X2lkIjoiOTI4NzM3Mzc5Nzk5MDkzIn0.Wy0hCBxhBJADdGp5AuCLlNYP--3lVaOa87WSm3eaiEiLNAlj_sF85CSTB6w-ufIX9hVMWFA6iCsTFXlweAgV-A7aPcO2pBeBGrBCNrfRqMFLFvKJ--sEH0FXuqk26nNVTmPCAEbrOBf6RC0vBh4NPPY8J4TWm-_X3dB9pBYvPxjhkShT0R4bkvrzCcPOwcYpw6KSCUd1TCjXusfTgHSz-93_wxnWTyLs8ouAJtuYl4WhhX33YpHTsk8P6EjenMEYGPfrSPEdZFraEen_WoMTzG6xrN-FhowFA3xzRmc5_aLlbST-ENp5sI9WNurbKGsDhMO5kVGUOYQRgWjghqMDQA", "expires_in": 1200}');
                return res;
            }

            // Handle trusted device API callouts
            if (req.getMethod() == 'POST') {
                res.setStatusCode(200);
                KountTrustedDeviceService.CreateResponse createResp = new KountTrustedDeviceService.CreateResponse();
                createResp.clientId = '900900';
                createResp.sessionId = 'abc123';
                createResp.userId = 'user456';
                createResp.deviceId = 'dev789';
                createResp.trustState = 'TRUSTED';
                createResp.friendlyName = 'Brad\'s Phone';
                createResp.createdAt = '2023-01-01T00:00:00.000Z';
                createResp.lastUpdated = '2023-01-01T00:00:00.000Z';
                res.setBody(JSON.serialize(createResp));
            } else if (req.getMethod() == 'DELETE') {
                res.setStatusCode(200);
                KountTrustedDeviceService.DeleteResponse deleteResp = new KountTrustedDeviceService.DeleteResponse();
                deleteResp.clientId = '900900';
                deleteResp.userId = 'user456';
                deleteResp.deviceId = 'dev789';
                res.setBody(JSON.serialize(deleteResp));
            } else {
                res.setStatusCode(400);
            }

            return res;
        }
    }

    @isTest
    static void testCreateTrustedDevice() {
        // Set up test data
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            ApiKey__c = 'testApiKey',
            AccessToken__c = 'testToken',
            ExpirationEpoch__c = DateTime.now().addMinutes(10).getTime() / 1000
        );
        insert config;

        // Set up mock
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        Test.startTest();
        KountTrustedDeviceService.CreateRequest input = new KountTrustedDeviceService.CreateRequest();
        input.clientId = '900900';
        input.sessionId = 'abc123';
        input.userId = 'user456';
        input.trustState = 'TRUSTED';
        input.friendlyName = 'Brad\'s Phone';

        KountTrustedDeviceService.CreateResponse res = KountTrustedDeviceService.createTrustedDevice(input);
        Test.stopTest();

        System.assertEquals('TRUSTED', res.trustState);
        System.assertEquals('user456', res.userId);
    }

    @isTest
    static void testDeleteTrustedDevice() {
        // Set up test data
        KountAuthConfig__c config = new KountAuthConfig__c(
            Name = 'Default',
            ApiKey__c = 'testApiKey',
            AccessToken__c = 'testToken',
            ExpirationEpoch__c = DateTime.now().addMinutes(10).getTime() / 1000
        );
        insert config;

        // Set up mock
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        Test.startTest();
        KountTrustedDeviceService.DeleteResponse res = KountTrustedDeviceService.deleteTrustedDevice('abc123', 'user456', '900900');
        Test.stopTest();

        System.assertEquals('900900', res.clientId);
        System.assertEquals('user456', res.userId);
    }
}