# Kount Account Protection for Salesforce (Apex)

This Apex app integrates with Kount's Account Protection service to submit Login, New Account Opening (NAO), and Challenge Decision events via REST API, authenticated with a JWT-based bearer token.

---

## 🔧 Setup Instructions

1. **Install/Deploy Both Apex Packages**
   - `jwt_auth`: handles JWT token generation and caching
   - `account_protection`: handles Login, NAO, and ChallengeOutcome API calls

2. **Create Remote Site Setting**
   Go to **Setup > Remote Site Settings** and create:
   - **Name**: `KountAPI`
   - **URL**: `https://api-sandbox.kount.com (Test) | https://api.kount.com (Prod)` 
   - **Active**: ✅

3. **Create Config Record**
   Go to **Developer Console > Query Editor**, and run this:
   ```soql
   INSERT INTO KountAuthConfig__c (Name, AccessToken__c, ExpirationEpoch__c)
   VALUES ('Default', 'your-initial-token-if-needed', 0)
   ```
   > The app will automatically update this with a fresh token if expired.

4. **Authorize Your Scratch Org** (if using SFDX)
   ```bash
   sf org login web --set-default
   sf project deploy start --source-dir k360/apex/jwt_auth/force-app
   sf project deploy start --source-dir k360/apex/account_protection/force-app
   ```

---

## 🔐 Login Decision Workflow

### 🔁 Flow
1. Customer attempts login.
2. Merchant sends Kount a Login Decision Request via `KountLoginService.sendLoginRequest()`.
3. Kount returns `ALLOW`, `CHALLENGE`, or `BLOCK`.
4. If `CHALLENGE` and client uses custom MFA, merchant must call ChallengeOutcome API.

### 🧪 Live Testing in Developer Console
Open **Developer Console > Execute Anonymous**, and run:

```apex
KountLoginService.LoginRequest req = new KountLoginService.LoginRequest();
req.inquiryId = 'test123';
req.channel = 'ACME_WEB';
req.deviceSessionId = 'device123';
req.userIp = '127.0.0.1';
req.loginUrl = 'https://example.com/login';

req.person = new KountLoginService.Person();
req.person.name = new KountLoginService.Name();
req.person.name.first = 'Jane';
req.person.name.last = 'Doe';
req.person.name.preferred = 'Janie';
req.person.emailAddress = 'jane@example.com';
req.person.phoneNumber = '+15555550123';
req.person.addresses = new List<KountLoginService.Address>{
    new KountLoginService.Address()
};

req.account = new KountLoginService.Account();
req.account.id = 'acct123';
req.account.type = 'STANDARD';
req.account.creationDateTime = '2024-01-01T12:12:12.000Z';
req.account.username = 'jane_doe';
req.account.userPassword = 'securehash';
req.account.accountIsActive = true;

req.strategy = new KountLoginService.Strategy();
req.strategy.mfaTemplateName = 'default_template';

// Ensure token is ready before sending the request
KountLoginService.ensureTokenReady();
HttpResponse res = KountLoginService.sendLoginRequest(req);
System.debug('Response: ' + res.getBody());
```

---

## 👤 New Account Opening (NAO)
> **Coming Soon** — this will follow the same pattern as the Login flow, with its own payload structure and endpoint.

---

## ✅ Challenge Decision API
> **Coming Soon** — this cross-cutting service is required if the merchant uses their **own MFA solution**. It submits the final outcome of a challenged login.

Will be implemented as: 
```apex
KountChallengeOutcomeService.sendChallengeOutcome(...)
```

---

## 📂 Project Structure
```
k360/
├── apex/
│   ├── jwt_auth/                # JWT handling
│   └── account_protection/     # Login, NAO, ChallengeOutcome logic
```

