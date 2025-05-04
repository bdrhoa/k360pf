global class KountTokenRefresher implements Schedulable {
    global void execute(SchedulableContext ctx) {
        System.enqueueJob(new KountTokenRefresherJob());
    }
}