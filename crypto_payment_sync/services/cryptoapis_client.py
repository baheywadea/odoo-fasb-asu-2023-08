import logging
import time
from urllib.parse import urljoin

import requests

from .exceptions import (
    CryptoApisConfigurationError,
    CryptoApisEndpointNotConfigured,
    CryptoApisRequestError,
    CryptoApisResponseError,
)

_logger = logging.getLogger(__name__)


class CryptoApisClient:
    """Read-only adapter for Crypto APIs data ingestion.

    The public Crypto APIs documentation describes product categories such as
    Address Latest, Address History, Transactions Data, Blockchain Utils,
    Market Data / Exchange Rates, and Blockchain Events. This client keeps the
    request mechanics centralized while avoiding guessed endpoint paths. Callers
    must provide an explicit endpoint path until a method is verified against
    the official API reference for a given chain/network.
    """

    DEFAULT_BASE_URL = "https://rest.cryptoapis.io/"

    def __init__(
        self,
        api_key=None,
        base_url=None,
        timeout=20,
        max_retries=2,
        backoff_seconds=1.0,
        session=None,
    ):
        self.api_key = api_key or ""
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    @property
    def masked_api_key(self):
        if not self.api_key:
            return ""
        if len(self.api_key) <= 8:
            return "****"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def _headers(self):
        if not self.api_key:
            raise CryptoApisConfigurationError("Crypto APIs API key is required for live requests.")
        return {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
        }

    def _url(self, path):
        if not path:
            raise CryptoApisEndpointNotConfigured(
                "Endpoint path is not configured. Verify the path in the official Crypto APIs documentation first."
            )
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def get_json(self, path, params=None):
        """Run a read-only GET request with retry/backoff and basic validation."""
        url = self._url(path)
        params = params or {}
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.timeout,
                )
                if response.status_code >= 500 and attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                if response.status_code >= 400:
                    raise CryptoApisRequestError(
                        f"Crypto APIs request failed with HTTP {response.status_code}."
                    )
                try:
                    return response.json()
                except ValueError as exc:
                    raise CryptoApisResponseError("Crypto APIs response was not valid JSON.") from exc
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.backoff_seconds * (attempt + 1))
                    continue
                raise CryptoApisRequestError("Crypto APIs request failed after retries.") from exc

        raise CryptoApisRequestError("Crypto APIs request failed after retries.") from last_error

    def validate_address(self, *, endpoint_path=None, payload=None):
        """Placeholder for Blockchain Utils address validation.

        The official docs identify address validation under Blockchain Utils,
        with chain-specific tools. This method intentionally requires a verified
        endpoint path before use.
        """
        if payload is not None:
            _logger.debug("Address validation payload prepared without logging sensitive values.")
        return self.get_json(endpoint_path)

    def get_address_balance(self, *, endpoint_path=None, params=None):
        """Read address balance using a caller-supplied, verified Address Latest path."""
        return self.get_json(endpoint_path, params=params)

    def list_transactions_by_address(self, *, endpoint_path=None, params=None):
        """Read address transactions using a verified Address Latest or Address History path."""
        return self.get_json(endpoint_path, params=params)

    def get_transaction_details(self, *, endpoint_path=None, params=None):
        """Read transaction details using a verified Transactions Data path."""
        return self.get_json(endpoint_path, params=params)

    def list_token_transfers(self, *, endpoint_path=None, params=None):
        """Read token-transfer details using a verified chain-specific path."""
        return self.get_json(endpoint_path, params=params)

    def get_exchange_rate(self, *, endpoint_path=None, params=None):
        """Read exchange-rate data using a verified Market Data / Exchange Rates path."""
        return self.get_json(endpoint_path, params=params)

    def list_blockchain_event_subscriptions(self, *, endpoint_path=None, params=None):
        """Read blockchain event subscriptions using a verified Blockchain Events path."""
        return self.get_json(endpoint_path, params=params)
