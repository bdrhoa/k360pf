# Salesforce Named Credential Integration for Kount JWT Authentication

This guide provides step-by-step instructions for setting up Salesforce to retrieve an access token from Kount using **Named Credentials** and **External Credentials**. This integration uses the latest Salesforce configuration (Spring 2025+).

---

## 📌 Prerequisites

- Salesforce Scratch Org or Sandbox
- Access to Setup permissions
- API Key from Kount (in base64 encoded `username:password` format)

---

## ✅ Goal

Allow Apex code to authenticate with Kount using a Named Credential secured via Custom Setting.

---

## 📁 Project Structure

```
force-app/
└── main/
    └── default/
        ├── classes/
        │   └── KountJwtAuth.cls
        └── objects/
            └── KountAuthSetting__c/
                ├── KountAuthSetting__c.object
                └── fields/
                    └── ApiKey__c.field-meta.xml
```

---

## 🛠️ Salesforce Setup Steps

### 1. Create Custom Setting to Store the API Key

1. Go to **Setup → Custom Settings → New**.
2. Fill in the following:
   - **Label**: `Kount Auth Setting`
   - **Object Name**: `KountAuthSetting`
   - **Setting Type**: `Hierarchy`
   - **Visibility**: `Public`
3. Click **Save**.
4. Add a custom field:
   - **Field Label**: `API Key`
   - **Field Name**: `ApiKey`
   - **Type**: `Text`, Length: `255`

#### ⚠️ Example

| Label      | Field Name  | Type |
|------------|-------------|------|
| API Key    | ApiKey__c   | Text |

---

### 2. Enter API Key in the Custom Setting

1. In **Setup**, search for **Custom Settings**.
2. Click **Manage** next to `Kount Auth Setting`.
3. Click **New** to create a default organization-level setting.
4. Paste your base64-encoded `username:password` string in the **API Key** field.

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
        +--> Custom Setting (API Key)                       |
              KountAuthSetting__c                          |
```

---

## 🧪 Testing Locally in Salesforce

- Use **Developer Console → Execute Anonymous Window**:
```apex
System.debug(KountJwtAuth.getAccessToken());
```

---

## ✅ Done!

You're now securely retrieving JWT access tokens from Kount via Salesforce using Named Credentials and External Credentials. 🎉
