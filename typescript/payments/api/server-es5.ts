/**
 * Usage Instructions:
 * 
 * 1. Install dependencies:
 *    npm install express axios axios-retry jsonwebtoken timers
 * 
 * 2. Set required environment variables:
 *    - KOUNT_API_KEY: Your API key for authentication.
 *    - KOUNT_PUBLIC_KEY: Your public key for webhook signature verification.
 * 
 * 3. Start the server:
 *    ts-node server-es5.ts
 * 
 * 4. Test the endpoint:
 *    curl --request POST \
 *      --url http://127.0.0.1:8000/process-transaction \
 *      --header 'Content-Type: application/json' \
 *      --data '{ "order_id": "12345", "transactions": [{ "processor": "PayPal", "payment": { "type": "PYPL", "payment_token": "TOKEN123" }, "subtotal": "1000", "order_total": "1050", "currency": "USD" }] }'
 * 
 * 5. The API handles automatic JWT token refreshing and retries failed requests with exponential backoff.
 */

var express = require('express');
var axios = require('axios');
var axiosRetry = require('axios-retry').default;
var jwt = require('jsonwebtoken');
var timersPromises = require('timers/promises');
var fs = require('fs');
var path = require('path');
var util = require('util');
var crypto = require('crypto');

var app = express();
app.use(express.json({
    verify: function(req, res, buf) {
      req.rawBody = buf.toString('utf8');
    }
  }));

var LOG_FILE = path.join(__dirname, 'kount.log');

function logError(message) {
  var logEntry = (new Date()).toISOString() + " - ERROR: " + message + "\n";
  fs.appendFileSync(LOG_FILE, logEntry);
}


var CVV_STATUSES = ["MATCH", "NO_MATCH", "NOT_PROVIDED"];
var AVS_STATUSES = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"];

// Function to simulate credit card authorization

function simulateCreditCardAuthorization(merchantOrderId) {
    var authResult = Math.random() < 0.9 ? "APPROVED" : "DECLINED";
    var cvvStatus = CVV_STATUSES[Math.floor(Math.random() * CVV_STATUSES.length)];
    var avsStatus = AVS_STATUSES[Math.floor(Math.random() * AVS_STATUSES.length)];

    return {
      merchantOrderId: merchantOrderId,
        transactions: [
            {
                authorizationStatus: {
                    authResult: authResult,
                    verificationResponse: {
                        cvvStatus: cvvStatus,
                        avsStatus: avsStatus,
                    },
                },
            },
        ],
    };
}

// Constants For API
var API_KEY = process.env.KOUNT_API_KEY;
var KOUNT_API_ENDPOINT = "https://api-sandbox.kount.com/commerce/v2/orders?riskInquiry=true";
var RETRY_INTERVAL = 10000; // 10 seconds
var REFRESH_BUFFER = 120; // 2 minutes before expiration

// Consts For Webhook
var WEBHOOK_URL = "https://api-sandbox.kount.com/commerce/v2/webhooks";
var publicKeyBase64 = process.env.KOUNT_PUBLIC_KEY;
if (!publicKeyBase64) {
  throw new Error("KOUNT_PUBLIC_KEY environment variable not set.");
}
var publicKey = crypto.createPublicKey({
  key: Buffer.from(publicKeyBase64, "base64"),
  format: "der",
  type: "spki",
});

var timestampGrace = 5 * 60 * 1000; // 5 minutes in milliseconds

if (!API_KEY) {
    throw new Error("API_KEY environment variable not set.");
}

// Apply axiosRetry globally
axiosRetry(axios, {
    retries: 3,
    retryDelay: axiosRetry.exponentialDelay,
    retryCondition: function(error) {
        return [403, 408, 429, 500, 502, 503, 504].indexOf((error.response && error.response.status) || 0) !== -1;
    },
});

var TokenManager = (function () {
    var instance;

    function createInstance() {
        var accessToken = null;
        var expiresAt = 0;

        function refreshToken() {
          axios({
              url: "https://login.kount.com/oauth2/ausdppkujzCPQuIrY357/v1/token",
              method: "post",
              headers: {
                  authorization: "Basic " + API_KEY,
              },
              params: {
                  grant_type: "client_credentials",
                  scope: "k1_integration_api",
              },
          })
          .then(function(response) {
              accessToken = response.data.access_token;
              var decoded = accessToken ? jwt.decode(accessToken) : null;
              expiresAt = decoded && decoded.exp ? decoded.exp : (Date.now() / 1000 + 3600);

              console.log("Token obtained:", accessToken);
          })
          .catch(function(error) {
              logError("Failed to fetch token: " + error);
          });
        }

        async function refreshTokenLoop() {
            while (true) {
                var waitTime = Math.max((expiresAt - Date.now() / 1000 - REFRESH_BUFFER) * 1000, RETRY_INTERVAL);
                await timersPromises.setTimeout(waitTime);
                try {
                    refreshToken();
                } catch (error) {
                    logError("Failed to fetch token: " + error);
                }
            }
        }

        refreshTokenLoop();

        return {
            getAccessToken: function() {
                var self = this;
                return new Promise(function(resolve) {
                    if (!accessToken || Date.now() / 1000 >= expiresAt - REFRESH_BUFFER) {
                        refreshToken();
                    }
                    timersPromises.setTimeout(100).then(function() {
                        resolve(accessToken);
                    });
                });
            }
        };
    }

    return {
        getInstance: function() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

var tokenManager = TokenManager.getInstance();

app.post('/process-transaction', function(req, res) {
    try {
      var payload = JSON.parse(JSON.stringify(req.body));
      console.log("Processing transaction:", JSON.stringify(payload, null, 2));
      processTransaction(payload).then(function(response) {
          res.json(response);
      }).catch(function(error) {
          logError("Failed to process transaction: " + error);
          res.status(500).json({ error: "Failed to process transaction" });
      });
    } catch (error) {
        logError("Failed to process transaction: " + error);
        res.status(500).json({ error: "Failed to process transaction" });
    }
});

function processTransaction(payload) {
    return new Promise(function(resolve) {
        tokenManager.getAccessToken().then(function(token) {
            axios.post(KOUNT_API_ENDPOINT, payload, {
                headers: {
                    Authorization: "Bearer " + token,
                    'Content-Type': 'application/json'
                }
            }).then(function(response) {
                var isPreAuth = payload.transactions.some(function(transaction) {
                    return !transaction.authorizationStatus || !transaction.authorizationStatus.authResult;
                });

                if (isPreAuth && response.data.order && response.data.order.orderId) {
                    setImmediate(function() {
                        patchTransaction(response.data.order.orderId, payload.order_id);
                    });
                }

                resolve(response.data);
            }).catch(function(error) {
                console.error("Error processing transaction", error);
                resolve({ order: { riskInquiry: { decision: "APPROVE" } } }); // Default response after failure
            });
        });
    });
}

function patchTransaction(kountOrderId, merchantOrderId) {
    return new Promise(function(resolve) {
        tokenManager.getAccessToken().then(function(token) {
            var url = KOUNT_API_ENDPOINT + "/" + kountOrderId;
            var simulatedAuthData = simulateCreditCardAuthorization(merchantOrderId);

            axios.patch(url, simulatedAuthData, {
                headers: {
                    Authorization: "Bearer " + token,
                    'Content-Type': 'application/json'
                }
            }).then(function(response) {
                resolve(response.data);
            }).catch(function(error) {
                logError("Failed to patch transaction: " + error);
                resolve({ order: { riskInquiry: { decision: "APPROVE" } } }); // Default response after failure
            });
        });
    });
}

// Express endpoint using the public key in verification
app.post("/kount360WebhookReceiver", function(req, res) {
    var timestampHeader = req.headers["x-event-timestamp"];
    var signatureBase64 = req.headers["x-event-signature"];
    if (!timestampHeader || !signatureBase64) {
      res.status(400).send({ error: "Missing required headers" });
      return;
    }
  
    var timestamp = new Date(timestampHeader);
    var now = new Date();
    // Assume timestampGrace is defined elsewhere
    if (
      isNaN(timestamp.getTime()) ||
      now.getTime() - timestamp.getTime() > timestampGrace ||
      timestamp.getTime() - now.getTime() > timestampGrace
    ) {
      res.status(400).send("Invalid timestamp");
      return;
    }
    var rawBody = req.rawBody;
    if (!rawBody) {
      res.status(400).send("Missing raw body");
      return;
    }

    // Verify the signature
    var verifier = crypto.createVerify("RSA-SHA256");
    verifier.update(Buffer.from(timestampHeader, 'utf8'));
    verifier.update(Buffer.from(rawBody, 'utf8'));
    verifier.end();
    
    var signature = Buffer.from(signatureBase64, "base64");
  
    var isVerified = verifier.verify(
      {
        key: publicKey,
        padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
        // Optionally, if needed:
        saltLength: crypto.constants.RSA_PSS_SALTLEN_DIGEST,
      },
      signature
    );
  
    if (!isVerified) {
      logError("Signature verification failed");
      console.log("Signature verification failed:", signature.toString("base64"));
      res.status(403).send("Could not verify signature");
      return;
    }
  
    // Process the valid webhook payload
    logError("Webhook received and verified successfully");
    console.log("Webhook payload:", JSON.stringify(req.body, null, 2));
    res.sendStatus(200);
  });

app.listen(8000, function() {
    logError("Server running on port 8000");
});

module.exports = { processTransaction: processTransaction, patchTransaction: patchTransaction, simulateCreditCardAuthorization: simulateCreditCardAuthorization };
