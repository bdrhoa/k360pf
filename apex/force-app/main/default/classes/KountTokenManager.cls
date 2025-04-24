public with sharing class KountTokenManager {
    public static String getToken() {
        KountAuthSetting__c setting = KountAuthSetting__c.getInstance('Default');
        if (setting == null || isExpired(setting)) {
            refreshToken();
            setting = KountAuthSetting__c.getInstance('Default');
        }
        return setting.AccessToken__c;
    }

    public static void refreshToken() {
        String newToken = KountJwtAuth.getAccessToken();
        Long expirationEpoch = DateTime.now().getTime() / 1000 + 3600;

        KountAuthSetting__c setting = KountAuthSetting__c.getInstance('Default');
        if (setting == null) {
            setting = new KountAuthSetting__c(Name = 'Default');
        }
        setting.AccessToken__c = newToken;
        setting.ExpirationEpoch__c = expirationEpoch;
        upsert setting;
    }

    private static Boolean isExpired(KountAuthSetting__c setting) {
        if (setting.ExpirationEpoch__c == null) return true;
        Long now = DateTime.now().getTime() / 1000;
        return now >= (Long)setting.ExpirationEpoch__c - 120;
    }
}