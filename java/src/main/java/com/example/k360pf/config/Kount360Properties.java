package com.example.k360pf.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "kount360")
public class Kount360Properties {
    private String authTokenUrl;
    private String apiBaseUrl;
    private String clientId;
    private String apiKey;
    private String merchantId;
    private String channel;

    private String signatureHeader;
    private String keyIdHeader;
    private String publicKeyPem;
    private String publicKeyUrl;
    private int publicKeyRefreshMinutes = 60;

    public String getAuthTokenUrl() { return authTokenUrl; }
    public void setAuthTokenUrl(String v) { this.authTokenUrl = v; }

    public String getApiBaseUrl() { return apiBaseUrl; }
    public void setApiBaseUrl(String v) { this.apiBaseUrl = v; }

    public String getClientId() { return clientId; }
    public void setClientId(String v) { this.clientId = v; }

    public String getApiKey() { return apiKey; }
    public void setApiKey(String v) { this.apiKey = v; }

    public String getMerchantId() { return merchantId; }
    public void setMerchantId(String v) { this.merchantId = v; }

    public String getChannel() { return channel; }
    public void setChannel(String v) { this.channel = v; }

    public String getSignatureHeader() { return signatureHeader; }
    public void setSignatureHeader(String v) { this.signatureHeader = v; }

    public String getKeyIdHeader() { return keyIdHeader; }
    public void setKeyIdHeader(String v) { this.keyIdHeader = v; }

    public String getPublicKeyPem() { return publicKeyPem; }
    public void setPublicKeyPem(String v) { this.publicKeyPem = v; }

    public String getPublicKeyUrl() { return publicKeyUrl; }
    public void setPublicKeyUrl(String v) { this.publicKeyUrl = v; }

    public int getPublicKeyRefreshMinutes() { return publicKeyRefreshMinutes; }
    public void setPublicKeyRefreshMinutes(int v) { this.publicKeyRefreshMinutes = v; }
}
