public class KountTokenRefresher implements Schedulable {
    public void execute(SchedulableContext context) {
        KountTokenManager.refreshToken();
    }
}