public with sharing class KountTokenManager {
    public static String getToken(KountAuthSetting__c injectedSetting) {
        KountAuthSetting__c setting = injectedSetting != null ? injectedSetting : KountAuthSetting__c.getInstance();
        if (setting == null || isExpired(setting)) {
            refreshToken(setting);
            setting = injectedSetting != null ? injectedSetting : KountAuthSetting__c.getInstance();
        }
        return setting.AccessToken__c;
    }

    public static String getToken() {
        return getToken(null);
    }

    public static void refreshToken(KountAuthSetting__c injectedSetting) {
        String newToken = KountJwtAuth.getAccessToken();
        Long expirationEpoch = DateTime.now().getTime() / 1000 + 3600;

        KountAuthSetting__c setting = injectedSetting != null ? injectedSetting : KountAuthSetting__c.getInstance('Default');
        if (setting == null) {
            setting = new KountAuthSetting__c(Name = 'Default');
        }
        setting.AccessToken__c = newToken;
        setting.ExpirationEpoch__c = expirationEpoch;
        upsert setting;
    }

    public static void refreshToken() {
        refreshToken(null);
    }

    private static Boolean isExpired(KountAuthSetting__c setting) {
        if (setting.ExpirationEpoch__c == null) return true;
        Long now = DateTime.now().getTime() / 1000;
        return now >= (Long)setting.ExpirationEpoch__c - 120;
    }
}