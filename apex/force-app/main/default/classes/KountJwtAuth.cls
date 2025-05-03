// KountJwtAuth.cls
// This class handles the JWT authentication for Kount API.
// It retrieves the access token using the client credentials grant type.
// It uses a custom setting to store the API key securely.
// The class includes detailed logging for debugging purposes.
// The class is designed to be used in a Salesforce environment.
// It is a part of the Kount integration package.   

/* 
Usage Example:

try {
    String token = KountJwtAuth.getAccessToken();
    System.debug('✅ Kount access token: ' + token);
} catch (Exception e) {
    System.debug('❌ Error getting token: ' + e.getMessage());
}
    
*/

public class KountJwtAuth {
    public static String getAccessToken() {
        Http http = new Http();
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:Kount_Auth/oauth2/ausdppkujzCPQuIrY357/v1/token');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/x-www-form-urlencoded');
        req.setHeader('Authorization', 'Basic ' + getApiKey());
        req.setBody('grant_type=client_credentials&scope=k1_integration_api');

        // 🔍 Log full request
        System.debug('🔍 Request Endpoint: ' + req.getEndpoint());
        System.debug('🔍 Request Method: ' + req.getMethod());
        System.debug('🔍 Request Headers: ' + req.getHeader('Authorization'));
        System.debug('🔍 Request Body: ' + req.getBody());

        HttpResponse res = http.send(req);
        if (res.getStatusCode() == 200) {
            Map<String, Object> body = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
            return (String) body.get('access_token');
        } else {
            throw new CalloutException('Token request failed: ' + res.getStatusCode() + ': ' + res.getBody());
        }
    }

    private static String getApiKey() {
        KountAuthSetting__c setting = KountAuthSetting__c.getInstance();
        if (setting == null || String.isBlank(setting.ApiKey__c)) {
            throw new CalloutException('Missing KOUNT_API_KEY in custom settings.');
        }
        return setting.ApiKey__c;
    }
}