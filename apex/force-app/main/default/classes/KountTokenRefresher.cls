public class KountTokenRefresher implements Schedulable {
    public static KountAuthSetting__c testSetting;

    public void execute(SchedulableContext context) {
        KountTokenManager.refreshToken(testSetting);
    }
}