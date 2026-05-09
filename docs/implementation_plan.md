# Implementation Plan

This plan upgrades the repository from documentation plus a payment-sync reference module into a stronger Odoo-native technical reference implementation for digital-asset accounting workflow support. It keeps all accounting, tax, audit, legal, and regulatory decisions subject to professional review.

## Development Principles

- Preserve existing `crypto_payment_sync` behavior unless a change is required for installability or clear safety.
- Keep the new Crypto APIs integration layer read-only.
- Do not implement transaction signing, broadcasting, private-key handling, seed phrase handling, custody, or funds movement.
- Do not invent unverified Crypto APIs endpoint paths or response schemas.
- Add adapter methods, normalizers, fixtures, and TODO notes where exact live API behavior needs validation.
- Separate implemented features from planned features in documentation.
- Keep outputs framed as reviewable support materials, not filings or professional advice.

## Phase 1: Baseline Quality

Expected files:

- `crypto_payment_sync/__manifest__.py`
- `crypto_payment_sync/models/__init__.py`
- `crypto_payment_sync/security/ir.model.access.csv`
- Existing XML view/menu files where needed.

Work:

- Normalize manifest formatting and load order.
- Keep security group references valid.
- Add new files to the manifest in controlled order.
- Run Python compilation, XML parsing, manifest parsing, and security CSV checks.

Risk:

- Full module install cannot be proven without an Odoo 19 database.

## Phase 2: Read-Only Crypto APIs Adapter

Expected files:

- `crypto_payment_sync/services/__init__.py`
- `crypto_payment_sync/services/cryptoapis_client.py`
- `crypto_payment_sync/services/normalizers.py`
- `crypto_payment_sync/services/exceptions.py`
- `sample_data/cryptoapis_*_sample.json`

Work:

- Add a pure Python adapter with configurable base URL, API key, timeout, retry/backoff, masked key display, response validation, and safe logging boundaries.
- Add category-specific placeholder methods for Address Latest, Address History, Transactions Data, Market Data/Exchange Rates, Blockchain Utils address validation, and Blockchain Events.
- Add normalizers that transform fixture-like payloads into normalized ledger dictionaries.

What will not be implemented now:

- Live endpoint path assertions for undocumented or unverified calls.
- Signing, broadcast, custody, private-key storage, or seed phrase handling.

## Phase 3: Normalized Digital-Asset Ledger

Expected files:

- `crypto_payment_sync/models/accounting_support.py`
- `crypto_payment_sync/views/crypto_accounting_support_views.xml`
- `crypto_payment_sync/views/crypto_menu.xml`
- `crypto_payment_sync/security/ir.model.access.csv`

Work:

- Add `crypto.normalized.transaction`.
- Track provider/source, network, wallet/address, raw source transaction reference, transaction hash, source ID, timestamp, asset, contract address, chain/network, quantity, fee, transaction type, counterparty, raw payload, payload hash, duplicate detection key, processing status, exception reason, and reviewer notes.
- Add database uniqueness on duplicate detection key.
- Mark uncertain records as `needs_review` instead of silently classifying them.

## Phase 4: Fair-Value Support

Expected files:

- `crypto_payment_sync/models/accounting_support.py`
- `crypto_payment_sync/views/crypto_accounting_support_views.xml`
- sample output files.

Work:

- Add `crypto.fair.value.measurement`.
- Capture asset, measurement date/time, pricing source, source provider, exchange rate, reporting currency, quantity, fair-value amount, carrying amount support, unrealized gain/loss support amount, valuation status, valuation policy notes, and reviewer notes.
- Do not certify valuation or determine principal market automatically.

## Phase 5: Journal-Entry Preparation

Expected files:

- `crypto_payment_sync/models/accounting_support.py`
- `crypto_payment_sync/views/crypto_accounting_support_views.xml`

Work:

- Add `crypto.journal.entry.preparation`.
- Add `crypto.journal.entry.preparation.line`.
- Support draft debit/credit preview lines, source transaction links, fair-value links, chart-of-account mapping fields, status, reviewer notes, and balancing checks.
- Do not auto-post account moves by default.

## Phase 6: Reconciliation and Audit Evidence

Expected files:

- `crypto_payment_sync/models/accounting_support.py`
- `crypto_payment_sync/views/crypto_accounting_support_views.xml`

Work:

- Add `crypto.reconciliation.status`.
- Add `crypto.audit.evidence.package`.
- Generate a simple Markdown summary for a review period with counts, exceptions, reconciliation status, reviewer notes, and disclaimer.

## Phase 7: Tax-Reporting Readiness

Expected files:

- `crypto_payment_sync/models/accounting_support.py`
- `crypto_payment_sync/views/crypto_accounting_support_views.xml`
- sample output files.

Work:

- Add `crypto.tax.readiness.1099da`.
- Add `crypto.form8949.reconciliation`.
- Store readiness and reconciliation support fields where data is available.
- Mark missing or judgment-heavy fields as `needs_review`.

What will not be implemented now:

- Official IRS forms.
- IRS submission or direct IRS integration.
- Tax advice or final tax positions.

## Phase 8: UI, Security, Documentation, and Samples

Expected files:

- `crypto_payment_sync/views/crypto_accounting_support_views.xml`
- `crypto_payment_sync/views/crypto_menu.xml`
- `crypto_payment_sync/security/ir.model.access.csv`
- `docs/cryptoapis_integration.md`
- `README.md`
- `crypto_payment_sync/README.md`
- `CHANGELOG.md`
- sample data and output files.

Work:

- Add menus for ingestion, accounting support, review, and tax-readiness records.
- Add search filters/group-by for provider, network, asset, status, period, review, and exceptions.
- Add groups for user, reviewer, and manager/configuration workflows.
- Update documentation to match implemented code.

## Testing Strategy

Run:

- `python3 -X pycache_prefix=/private/tmp/fasb_pycache -m compileall crypto_payment_sync`
- XML parse check for all `crypto_payment_sync/**/*.xml`.
- Manifest parse check.
- Security CSV sanity check.
- Unit tests for pure Python service/normalizer helpers, if added.

Full Odoo installation testing requires an Odoo 19 database and is outside this workspace unless explicitly available.
