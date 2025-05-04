public with sharing class KountTokenRefresherJob implements Queueable, Database.AllowsCallouts {
    public void execute(QueueableContext context) {
        KountAuthConfig__c config = [SELECT Id, Name, AccessToken__c, ExpirationEpoch__c, ApiKey__c FROM KountAuthConfig__c WHERE Name = 'Default' LIMIT 1];
        if (KountTokenManager.isExpired(config)) {
            KountTokenManager.refreshToken(config);
        }
    }
}