package com.example.k360pf.security;

import org.springframework.stereotype.Component;

import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.MGF1ParameterSpec;
import java.security.spec.PSSParameterSpec;
import java.util.Base64;

@Component
public class SignatureVerifier {
    private final PublicKeyProvider keyProvider;

    public SignatureVerifier(PublicKeyProvider keyProvider) {
        this.keyProvider = keyProvider;
    }

    /** Verifies RSA-PSS (SHA-256) signature over the raw request body. */
    public boolean verify(byte[] body, String base64Signature) {
        try {
            PublicKey pk = keyProvider.getPublicKey();
            Signature sig = Signature.getInstance("RSASSA-PSS");
            PSSParameterSpec pss = new PSSParameterSpec(
                    "SHA-256", "MGF1", MGF1ParameterSpec.SHA256, 32, 1);
            sig.setParameter(pss);
            sig.initVerify(pk);
            sig.update(body);
            byte[] sigBytes = Base64.getDecoder().decode(base64Signature);
            return sig.verify(sigBytes);
        } catch (Exception e) {
            return false;
        }
    }
}
