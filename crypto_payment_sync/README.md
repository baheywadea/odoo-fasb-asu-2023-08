# Crypto Payment Sync

`crypto_payment_sync` is an Odoo 19 reference module for digital-asset payment, transaction synchronization, and accounting workflow support. In this repository, it serves as the implemented foundation for a broader ERP-native digital-asset accounting and professional-review support framework.

The module demonstrates Odoo-native records and views for payment providers, wallets, wallet addresses, blockchain networks, crypto currencies, EVM transaction details, account payments, and payment transaction callbacks.

## Role in the Framework

This module supports the transaction ingestion and ERP traceability layer. It can provide source records that future accounting, fair-value, audit-evidence, and tax-reporting readiness layers may consume.

Implemented or inspectable areas include:

- Odoo payment-provider extension for crypto payment workflows.
- Digital-asset currency metadata fields.
- Blockchain, network, wallet, and wallet-address records.
- Payment transaction fields for crypto address, amount, public token, and transaction hash.
- QR payment page and status/callback controller routes.
- EVM transaction record structure and source transaction details.
- Odoo XML views, menus, access controls, data records, and frontend JavaScript.
- Read-only Crypto APIs adapter interfaces and fixture-based normalizers.
- Normalized digital-asset transaction records with duplicate-detection support.
- Fair-value measurement support records.
- Journal-entry preparation records and preview lines.
- Reconciliation status and audit evidence package records.
- 1099-DA readiness and Form 8949 reconciliation support records.

## Professional Review Boundary

This module does not provide accounting, tax, legal, audit, investment, regulatory, or security advice. It does not file returns, connect directly to IRS systems, certify fair value, replace professional reviewers, or guarantee compliance.

Any accounting or tax outputs derived from this module should be treated as reviewable support materials for qualified professionals.

## External API and Credential Handling

Some methods reference external API workflows and provider credentials. Use only sandbox or test credentials during development. Do not commit API keys, private keys, wallet seed phrases, webhook secrets, production logs, or real client data.

The new adapter layer under `services/` is read-only. Legacy local-wallet generation and transaction broadcast paths are disabled by default and require explicit test-only system-parameter opt-ins. Outbound payment execution, transaction signing, wallet management, or callback workflows require separate legal, regulatory, accounting, and security review before any production use.

## Development Notes

- Target Odoo version: 19.0.
- Declared dependencies: `account`, `website_sale`, and `payment`.
- License declared in manifest: LGPL-3.
- Main manifest: `crypto_payment_sync/__manifest__.py`.
- Access control file: `crypto_payment_sync/security/ir.model.access.csv`.

## Suggested Checks

From the repository root:

```bash
python3 -m compileall crypto_payment_sync
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
for path in Path("crypto_payment_sync").rglob("*.xml"):
    ET.parse(path)
print("XML parse check passed")
PY
python3 -m unittest tests/test_services.py
```

Full functional validation requires an Odoo 19 development database and configured test credentials.
