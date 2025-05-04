public with sharing class KountTokenManager {
    public static String getToken(KountAuthConfig__c injectedSetting) {
        KountAuthConfig__c setting = injectedSetting != null ? injectedSetting : [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
        if (setting == null || isExpired(setting)) {
            refreshToken(setting);
            if (injectedSetting == null) {
                setting = [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
            }
            // else: keep using the injected setting, which was updated in refreshToken()
        }
        return setting.AccessToken__c;
    }

    public static String getToken() {
        return getToken(null);
    }

    public static void refreshToken(KountAuthConfig__c injectedSetting) {
        String newToken = KountJwtAuth.getAccessToken();
        Long expirationEpoch = DateTime.now().getTime() / 1000 + 3600;

        KountAuthConfig__c setting = injectedSetting != null ? injectedSetting : [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
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

    @testVisible 
    private static Boolean isExpired(KountAuthConfig__c setting) {
        if (setting.ExpirationEpoch__c == null) return true;
        Long now = DateTime.now().getTime() / 1000;
        return now >= (Long)setting.ExpirationEpoch__c - 120;
    }
}