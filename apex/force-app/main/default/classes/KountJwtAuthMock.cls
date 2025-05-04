@isTest
global class KountJwtAuthMock implements HttpCalloutMock {
    global HTTPResponse respond(HTTPRequest req) {
        HttpResponse res = new HttpResponse();
        res.setHeader('Content-Type', 'application/json');
        res.setBody('{"access_token": "mockedToken", "expires_in": 3600}');
        res.setStatusCode(200);
        return res;
    }
}