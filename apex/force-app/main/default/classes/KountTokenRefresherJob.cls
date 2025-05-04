public with sharing class KountTokenRefresherJob implements Queueable, Database.AllowsCallouts {
    public void execute(QueueableContext context) {
        KountAuthConfig__c config = KountTokenManager.getConfig();
        if (KountTokenManager.isExpired(config)) {
            KountTokenManager.refreshToken(config);
        }
    }
}