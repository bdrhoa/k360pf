# Salesforce Named Credential Integration for Kount JWT Authentication

This guide provides step-by-step instructions for setting up Salesforce to retrieve an access token from Kount using **Named Credentials** and **External Credentials**. This integration uses the latest Salesforce configuration (Spring 2025+).

---

## 📌 Prerequisites

- Salesforce Scratch Org or Sandbox
- Access to Setup permissions
- API Key from Kount (in base64 encoded `username:password` format)

---

## ✅ Goal

Allow Apex code to authenticate with Kount using a Named Credential secured via Custom Object.

---

## 📁 Project Structure

```
force-app/
└── main/
    └── default/
        ├── classes/
        │   └── KountJwtAuth.cls
        └── objects/
            └── KountAuthConfig__c/
                ├── KountAuthConfig__c.object
                └── fields/
                    ├── ApiKey__c.field-meta.xml
                    ├── AccessToken__c.field-meta.xml
                    └── ExpirationEpoch__c.field-meta.xml
```

---

## 🛠️ Salesforce Setup Steps

### 1. Create Custom Object to Store API Key and Tokens

1. Go to **Setup → Object Manager → Create → Custom Object**.
2. Fill in the following:
   - **Label**: `Kount Auth Config`
   - **Plural Label**: `Kount Auth Configs`
   - **Object Name**: `KountAuthConfig`
   - **Record Name**: `Name` (Text)
   - **Allow Reports**, **Allow Activities**: as needed
3. Click **Save**.
4. Add custom fields:
   - **API Key**
     - **Field Label**: `API Key`
     - **Field Name**: `ApiKey`
     - **Data Type**: `Text`, Length: `255`
   - **Access Token**
     - **Field Label**: `Access Token`
     - **Field Name**: `AccessToken`
     - **Data Type**: `Text Area (Long)`
   - **Expiration Epoch**
     - **Field Label**: `Expiration Epoch`
     - **Field Name**: `ExpirationEpoch`
     - **Data Type**: `Number`, Length: `18`, Decimal Places: `0`

---

### 2. Enter API Key and Initialize Token Records

1. In **Setup → Object Manager**, find `Kount Auth Config`.
2. Click **Tab** and create a tab if needed.
3. Go to the `Kount Auth Configs` tab.
4. Click **New** to create a record.
5. Enter a Name (e.g., `Default`).
6. Paste your base64-encoded `username:password` string in the **API Key** field.
7. Leave **Access Token** and **Expiration Epoch** blank initially.
8. Save the record.

---

### 3. Create External Credential

1. Go to **Setup → Named Credentials → External Credentials → New**.
2. Name: `Kount_External`
3. Authentication Protocol: `Custom`
4. Click **Save**

#### Create Principal

- **Parameter Name**: `Authorization`
- **Sequence Number**: `1`
- **Identity Type**: `Named Principal`
- **Authentication Parameter**
  - **Name**: `Authorization`
  - **Value**: `Basic <YOUR-BASE64-AUTH-TOKEN>`

---

### 4. Assign Permission Set

1. Go to **Setup → Permission Sets → New**.
2. Name: `Kount JWT Access`
3. Save the permission set.
4. Under **External Credential Principal Access**, add:
   - **Kount_External** → Principal created above
5. Assign this permission set to your user.

---

### 5. Create Named Credential

1. Go to **Setup → Named Credentials → New**.
2. Label: `Kount Auth`
3. Name: `Kount_Auth`
4. URL: `https://login.kount.com`
5. External Credential: `Kount_External`
6. Click **Save**

---

## 💻 Apex Usage

```apex
String token = KountJwtAuth.getAccessToken();
System.debug('🔑 Token: ' + token);
```

---

## 📊 Architecture Diagram

```plaintext
+----------------+       +----------------------+       +--------------------+
| Apex Class     | ----> | Named Credential     | ----> | External Credential|
| KountJwtAuth   |       | Kount_Auth           |       | Kount_External     |
+----------------+       +----------------------+       +--------------------+
        |                        |                            |
        |                        +--> Base URL                |
        |                        +--> Authorization Header    |
        |                                                   |
        +--> Custom Object (API Key & Token Storage)        |
              KountAuthConfig__c                            |
```

---

## 🧪 Testing Locally in Salesforce

- Use **Developer Console → Execute Anonymous Window**:
```apex
System.debug(KountJwtAuth.getAccessToken());
```

---

## 🔁 Automatic Token Refresh

To refresh your Kount JWT token automatically, you can use a scheduled Apex job.

### 1. Create the Scheduler Class

Ensure you have a class like this:

```apex
global class KountTokenRefresher implements Schedulable {
    global void execute(SchedulableContext ctx) {
        try {
            String token = KountJwtAuth.getAccessToken();
            System.debug('🔄 Refreshed token: ' + token);
        } catch (Exception e) {
            System.debug('❌ Token refresh failed: ' + e.getMessage());
        }
    }
}
```

### 2. Schedule the Job via Developer Console

Open **Execute Anonymous Window** in Developer Console and run:

```apex
// Every 15 minutes using 4 separate jobs
System.schedule('KountTokenRefresher 00', '0 0 * * * ?', new KountTokenRefresher());
System.schedule('KountTokenRefresher 15', '0 15 * * * ?', new KountTokenRefresher());
System.schedule('KountTokenRefresher 30', '0 30 * * * ?', new KountTokenRefresher());
System.schedule('KountTokenRefresher 45', '0 45 * * * ?', new KountTokenRefresher());
```

You can verify the scheduled job by querying:

```apex
List<CronTrigger> jobs = [
    SELECT Id, CronJobDetail.Name, NextFireTime 
    FROM CronTrigger 
    WHERE CronJobDetail.Name LIKE 'KountTokenRefresher%'
];
for (CronTrigger job : jobs) {
    System.debug('📅 Job: ' + job.CronJobDetail.Name + ' | Next run: ' + job.NextFireTime);
}
```

## ✅ Done!

You're now securely retrieving JWT access tokens from Kount via Salesforce using Named Credentials and External Credentials. 🎉
