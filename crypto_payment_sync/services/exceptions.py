class CryptoApisError(Exception):
    """Base exception for read-only Crypto APIs adapter errors."""


class CryptoApisConfigurationError(CryptoApisError):
    """Raised when adapter configuration is missing or unsafe."""


class CryptoApisEndpointNotConfigured(CryptoApisConfigurationError):
    """Raised when a live endpoint path has not been explicitly configured."""


class CryptoApisRequestError(CryptoApisError):
    """Raised when a read-only request fails after retries."""


class CryptoApisResponseError(CryptoApisError):
    """Raised when a response cannot be parsed or validated."""
