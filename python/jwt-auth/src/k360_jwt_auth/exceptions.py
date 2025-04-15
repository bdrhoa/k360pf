class InvalidSignatureError(Exception):
    """Raised when the signature is missing, improperly formatted, or does not match."""
    pass

class TimestampTooOldError(Exception):
    """Raised when the timestamp is older than the allowed grace period."""
    pass

class TimestampTooNewError(Exception):
    """Raised when the timestamp is newer than the allowed grace period."""
    pass

class MissingPublicKeyError(Exception):
    """Raised when no public key is available to verify the signature."""
    pass

class PublicKeyExpiredError(Exception):
    """Raised when the loaded public key is expired."""
    pass