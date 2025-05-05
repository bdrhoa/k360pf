public with sharing class KountTokenManager {
    public static String getToken(KountAuthConfig__c injectedSetting) {
        KountAuthConfig__c setting;
        if (injectedSetting != null) {
            setting = injectedSetting;
        } else {
            List<KountAuthConfig__c> configs = [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
            if (configs.isEmpty()) {
                throw new AuraHandledException('No KountAuthConfig__c record found with Name = Default');
            }
            setting = configs[0];
        }
        if (setting == null || isExpired(setting)) {
            refreshToken(setting);
            if (injectedSetting == null) {
                List<KountAuthConfig__c> configs = [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
                if (configs.isEmpty()) {
                    throw new AuraHandledException('No KountAuthConfig__c record found with Name = Default');
                }
                setting = configs[0];
            }
            // else: keep using the injected setting, which was updated in refreshToken()
        }
        return setting.AccessToken__c;
    }

    public static String getToken() {
        return getToken(null);
    }

    public static Long getExpirationEpochFromJwt(String jwtToken) {
        // JWT format: header.payload.signature
        String[] parts = jwtToken.split('\\.');
        if (parts.size() != 3) {
            throw new IllegalArgumentException('Invalid JWT format');
        }
    
        String payloadJson = EncodingUtil.urlDecode(parts[1], 'UTF-8');
        Blob payloadBlob = EncodingUtil.base64Decode(payloadJson);
        String decodedPayload = payloadBlob.toString();
    
        Map<String, Object> payloadMap = (Map<String, Object>) JSON.deserializeUntyped(decodedPayload);
        if (!payloadMap.containsKey('exp')) {
            throw new IllegalArgumentException('JWT is missing "exp" claim');
        }
    
        return Long.valueOf(String.valueOf(payloadMap.get('exp')));
    }

    public static void refreshToken(KountAuthConfig__c injectedSetting) {
        String newToken = KountJwtAuth.getAccessToken();
        if (newToken == null || String.isEmpty(newToken)) {
            throw new AuraHandledException('Failed to retrieve access token');
        }

        Long expirationEpoch = getExpirationEpochFromJwt(newToken);

        if (expirationEpoch == null) {
            throw new AuraHandledException('Failed to retrieve expiration epoch from JWT');
        }
        if (expirationEpoch <= 0) {
            throw new AuraHandledException('Invalid expiration epoch from JWT');
        }

        KountAuthConfig__c setting;
        if (injectedSetting != null) {
            setting = injectedSetting;
        } else {
            List<KountAuthConfig__c> configs = [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
            if (configs.isEmpty()) {
                throw new AuraHandledException('No KountAuthConfig__c record found with Name = Default');
            }
            setting = configs[0];
        }
        if (setting == null) {
            setting = new KountAuthConfig__c(Name = 'Default');
        }
        setting.AccessToken__c = newToken;
        setting.ExpirationEpoch__c = expirationEpoch;
        upsert setting;
    }

    public static void refreshToken() {
        refreshToken(null);
    }

    public static Boolean isExpired(KountAuthConfig__c setting) {
        if (setting.ExpirationEpoch__c == null) return true;
        Long now = DateTime.now().getTime() / 1000;
        return now >= (Long)setting.ExpirationEpoch__c - 120;
    }
}