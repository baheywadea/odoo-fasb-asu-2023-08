# Current State

This repository currently centers on one Odoo 19 addon: `crypto_payment_sync`.

The module is a reference implementation for crypto payment and transaction synchronization workflows in Odoo. It already contains practical ERP integration surfaces for payment providers, wallet/source-account records, wallet addresses, blockchain networks, crypto currencies, EVM transaction details, account payments, payment transaction callbacks, QR/status pages, scheduled actions, security access rules, and documentation.

## Existing Module Purpose

`crypto_payment_sync` extends Odoo payment and accounting objects so digital-asset payment workflows can be represented inside Odoo. Its current strength is transaction/payment traceability: provider records, wallet/address records, blockchain/network metadata, EVM transaction records, payment transaction metadata, account payment links, and webhook-style callback handling.

## Existing Odoo Models

Implemented models and extensions include:

- `payment.provider` extension for the `crypto` provider code and Crypto APIs credential field.
- `res.currency` extension for crypto/fiat classification and Crypto APIs reference IDs.
- `crypto.blockchain` for blockchain metadata.
- `crypto.network` for chain/network configuration.
- `crypto.wallet` for wallet/source-account style records, network links, balances, provider links, and address relationships.
- `crypto.wallet.address` for wallet addresses, balances, event subscriptions, and payment transaction links.
- `crypto.wallet.address.event` for callback/event subscription metadata.
- `crypto.transaction` as an early generic transaction placeholder with invoice matching status.
- `crypto.transaction.evm` for EVM transaction details, hashes, fees, value, gas, block metadata, sender/recipient, and wallet/address links.
- `payment.transaction` extension for crypto payment address, amount, public token, transaction hash, and rendering/process helpers.
- `account.payment` extension for crypto address links and crypto transaction references.
- `account.journal` extension with an `is_crypto` marker.
- `res.partner.crypto.address` and `res.partner` extension for partner crypto addresses.

## Existing Controllers and Routes

`crypto_payment_sync/controllers/crypto_payment_controller.py` currently includes:

- `/crypto/pay/<tx_id>` public payment page route.
- `/crypto/qr/<tx_id>.png` QR image route.
- `/crypto/status/<tx_id>` JSON-RPC payment status route.
- `/invoice_link/crypto/callback/<tx_id>` callback route.
- `/crypto/intent/<tx_id>` JSON-RPC intent route.
- `/crypto/wc_tx/<tx_id>` JSON-RPC transaction-hash capture route.

These routes support payment workflow UX and callback traceability. They do not create an accounting fair-value layer or tax-readiness layer by themselves.

## Existing Views and Menus

The module has XML views for:

- Crypto payment provider configuration.
- Crypto currencies.
- Generic crypto transactions.
- EVM transactions.
- Blockchains.
- Networks.
- Wallets.
- Wallet addresses.
- Wallet address events.
- Partner crypto addresses.
- Account journals and account payments.
- Website payment templates.

The current menu root is `Crypto APIS`, with payment providers, transactions, and configuration menus. The new accounting-support workflow should add clear menus for ingestion, accounting support, review, and tax-reporting readiness while preserving existing records.

## Existing Scheduled Jobs

`crypto_payment_sync/data/cron.xml` contains:

- A server action named `Compute Rate` that calls `res.currency.get_rate()` for selected currency records.
- An hourly cron named `Fetch Crypto Transactions` that calls `crypto.transaction.fetch_crypto_transactions()`.

The generic transaction fetch method is currently a placeholder. Existing wallet/address methods contain API-oriented retrieval logic, but there is not yet a separated read-only adapter layer with fixtures and normalization.

## Existing Payment and Crypto Flow

The current payment flow can:

1. Configure a crypto payment provider.
2. Link wallets and wallet addresses to provider/network records.
3. Render a crypto payment page with a QR code.
4. Store public payment tokens and transaction hashes.
5. Receive callback payloads.
6. Create or update EVM transaction records.
7. Link crypto transaction records to Odoo payment/accounting objects.

This supports source traceability and payment workflow evidence. The repository now also includes prototype normalized transaction, fair-value measurement, journal-entry preparation, reconciliation, audit evidence package, and tax-reporting readiness records for professional-review support.

## Existing Limitations

- API calls from Odoo models are routed through provider-level Crypto APIs helpers where practical; the standalone `services/` adapter remains available for fixture-driven tests and future separation.
- Some legacy methods reference outbound payment, transaction preparation, signing, broadcast, mnemonic, or private-key-adjacent workflows. Those paths are disabled by default through system parameters and are outside the recommended read-only accounting-support scope.
- The generic `crypto.transaction.fetch_crypto_transactions()` method is still a placeholder.
- Normalized accounting-support records exist as prototype Odoo models and still need broader functional validation in an Odoo 19 database.
- Duplicate detection exists for normalized transaction records and should be expanded across live ingestion flows.
- Fair-value, journal-entry preparation, reconciliation, audit evidence, 1099-DA readiness, and Form 8949 support records exist as reviewable support models; they are not final filings or professional determinations.
- Full Odoo installation testing has not been run in this workspace.

## Implemented Versus Planned

Implemented before the accounting-support upgrade:

- Odoo crypto payment provider extension.
- Wallet, address, blockchain, network, currency, EVM transaction, partner address, account payment, and payment transaction extensions.
- Payment page, QR code, status, callback, intent, and transaction-hash capture routes.
- Odoo views, menus, seed records, security access CSV, frontend JavaScript, and sample/documentation files.

Implemented in the current accounting-support upgrade:

- Read-only Crypto APIs adapter interface with safe request handling and fixtures.
- Normalized digital-asset ledger model with duplicate-detection support.
- Fair-value measurement support model.
- Journal-entry preparation support model and preview lines.
- Reconciliation status and audit evidence package models.
- 1099-DA readiness and Form 8949 reconciliation support models.
- Odoo views/menus/security for the accounting-support workflow.
- Fake Crypto APIs-style fixtures and pure Python normalizer tests.

Still needed for a stronger future implementation:

- Verified live endpoint paths for each supported Crypto APIs category.
- Full Odoo 19 installation testing.
- Odoo transaction ingestion wizards or scheduled jobs using the read-only adapter.
- Broader tests for Odoo model constraints, journal-entry balancing in an Odoo database, and audit package generation.
- Practitioner review of accounting, valuation, tax-readiness, and internal-control assumptions.
