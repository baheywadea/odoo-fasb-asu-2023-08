# Crypto APIs Integration

This project uses Crypto APIs as a reference read-only data source for blockchain/payment-data ingestion. The integration is designed to support accounting workflow preparation, traceability, fair-value support, and professional review. It does not implement custody, private-key handling, transaction signing, transaction broadcasting, or funds movement.

Official documentation reference: <https://developers.cryptoapis.io/v-2.2024-12-12-175/RESTapis/general-information/overview>

## Read-Only Scope

The adapter layer in `crypto_payment_sync/services/` is intentionally read-only. It provides request handling and method boundaries for:

- Blockchain Utils address validation.
- Address Latest activity and balance lookup.
- Address History transaction lookup.
- Transactions Data transaction-detail lookup.
- Market Data / Exchange Rates pricing inputs for fair-value support.
- Blockchain Events subscription lookup or future webhook-support planning.

Where exact endpoint paths or response schemas need chain-specific verification, adapter methods require a caller-supplied `endpoint_path` and raise a clear configuration error if one is not provided. This avoids guessing production API paths.

## Credential Handling

- API keys should be stored in Odoo configuration records and restricted to manager-level users.
- The provider form displays a masked key for ordinary review.
- The adapter exposes a masked API key helper for logs or diagnostics.
- Do not log API keys, webhook secrets, private keys, seed phrases, or real client data.

## Adapter Files

- `crypto_payment_sync/services/cryptoapis_client.py` - read-only HTTP adapter with base URL, headers, timeout, retry/backoff, masked key display, and response validation.
- `crypto_payment_sync/services/normalizers.py` - fixture-tolerant normalization helpers for transaction and exchange-rate payloads.
- `crypto_payment_sync/services/exceptions.py` - adapter exception classes.

## Fixture Mapping

Fake fixtures are provided for development and tests:

- `sample_data/cryptoapis_evm_transactions_sample.json`
- `sample_data/cryptoapis_utxo_transactions_sample.json`
- `sample_data/cryptoapis_exchange_rates_sample.json`

The current normalizer maps EVM-style transaction data into a normalized dictionary containing:

- source provider
- source transaction ID
- transaction hash
- timestamp
- asset symbol
- quantity
- fee quantity and fee asset
- network
- payload hash
- duplicate key
- processing status
- reviewer notes

Ambiguous transaction classification defaults to `unknown` and `needs_review`.

## Odoo Mapping

Normalized dictionaries can be stored in `crypto.normalized.transaction` through `create_from_normalized_dict()`. The normalized transaction can then link to:

- `crypto.fair.value.measurement`
- `crypto.journal.entry.preparation`
- `crypto.reconciliation.status`
- `crypto.audit.evidence.package`
- `crypto.tax.readiness.1099da`
- `crypto.form8949.reconciliation`

## Retries and Rate Limits

The adapter supports simple retry/backoff for transient request failures. Production deployments should align retry settings with the active Crypto APIs plan, rate limits, and operational monitoring.

## Testing

Run pure Python normalizer tests without a live API key:

```bash
python3 -m unittest tests/test_services.py
```

Live API testing requires a verified endpoint path, sandbox or test credentials where available, and a separate Odoo development environment.
