# ERP-Native Digital-Asset Accounting and Compliance Infrastructure Framework

This repository provides a public reference implementation and documentation package for mapping digital-asset transaction data into ERP accounting workflows, CPA-reviewable audit evidence, and structured tax-reporting readiness outputs.

The current codebase centers on an Odoo 19 module, `crypto_payment_sync`, that demonstrates digital-asset payment and transaction-record synchronization patterns. The surrounding documentation describes an implementation pathway for extending those patterns into FASB ASU 2023-08 fair-value accounting support, IRS Form 1099-DA field-mapping readiness, and IRS Form 8949 reconciliation support.

Wording is intentionally conservative: this repository is a reference implementation and standards-mapping framework, not a government-approved filing system or substitute for professional review.

![License: LGPL-3.0](https://img.shields.io/badge/License-LGPL--3.0-blue.svg)
![Odoo Version](https://img.shields.io/badge/Odoo-19.0-714B67)
![Status](https://img.shields.io/badge/Status-Reference%20Implementation-orange)

## What the Project Supports

- Digital-asset transaction ingestion and synchronization inside Odoo.
- A normalized digital-asset ledger concept for transaction, wallet, network, and provider records.
- ERP journal-entry preparation and accounting traceability workflows.
- FASB ASU 2023-08 fair-value measurement support, including mapping concepts for transaction-date and reporting-date valuation.
- CPA-reviewable audit evidence package design, including source references, reconciliation status, and reviewer notes.
- IRS Form 1099-DA field-mapping readiness for future information-reporting workflows.
- IRS Form 8949 reconciliation support for demonstration-level disposition reporting.

## What the Project Does Not Do

- It does not provide tax, accounting, legal, audit, investment, or regulatory advice.
- It does not file tax returns or information returns.
- It does not connect directly to IRS systems.
- It does not replace CPAs, auditors, tax preparers, attorneys, or internal control reviewers.
- It is not government-approved and does not claim endorsement by any agency or standards body.
- It does not guarantee compliance without professional review.
- It does not guarantee adoption, deployment, or suitability for any specific taxpayer, entity, jurisdiction, or reporting period.

All accounting and tax-related outputs should be treated as reviewable support materials for qualified professionals, not final filings or legal/tax conclusions.

## Intended Users

- ERP implementers and Odoo developers.
- CPAs and accounting professionals.
- Tax preparers and tax-technology reviewers.
- Fintech and payment API integrators.
- SMEs with digital-asset accounting and reconciliation needs.
- Researchers evaluating reusable ERP-native compliance infrastructure.

## Repository Structure

```text
.
├── crypto_payment_sync/                  # Odoo 19 reference module for crypto payment and transaction synchronization
│   ├── controllers/                      # Public payment, QR, status, and callback routes
│   ├── data/                             # Odoo seed records and scheduled actions
│   ├── models/                           # Odoo models for currencies, wallets, networks, transactions, and payments
│   ├── security/                         # Odoo access control CSV
│   ├── static/                           # Module marketplace assets and frontend JavaScript
│   ├── views/                            # Odoo XML views, menus, and templates
│   └── __manifest__.py                   # Odoo module manifest
├── docs/                                 # Architecture, standards mapping, professional-review scope, and disclaimers
├── examples/                             # Demonstration workflow notes
├── sample_data/                          # Fake input transaction data for documentation and testing
├── sample_outputs/                       # Fake output examples for reviewable support materials
├── AGENTS.md                             # Instructions for future coding agents
├── CONTRIBUTING.md                       # Contribution guidance
├── SECURITY.md                           # Security reporting and data-handling policy
├── CHANGELOG.md                          # Project change history
├── LICENSE                               # LGPL-3.0 license text
└── README.md                             # Project overview
```

## Quick Start

The repository currently provides an Odoo module plus documentation and demonstration data. The complete compliance engine and reporting modules described in the roadmap are planned implementation phases.

### Documentation-Only Review

```bash
git clone <repository-url>
cd odoo-fasb-asu-2023-08
ls docs sample_data sample_outputs examples
```

Review the architecture and standards-mapping documents in `docs/`. The sample files use fake data only and are intended to demonstrate expected input and output shapes.

### Prototype Odoo Module Review

1. Use an Odoo 19 development environment with the `account`, `website_sale`, and `payment` modules available.
2. Add this repository path to the Odoo addons path.
3. Install the `crypto_payment_sync` module in a development database.
4. Configure only test or sandbox credentials. Do not commit credentials, private keys, webhook secrets, or real client data.
5. Review generated or synchronized records with a qualified accounting, tax, and technical reviewer before using any workflow outside a test environment.

No production accounting use is claimed by this repository. External API behavior, credentials, Odoo edition differences, and jurisdiction-specific requirements require separate validation.

## Example Workflow

```text
source transaction
  -> ingestion
  -> normalization
  -> fair-value record
  -> journal-entry preparation
  -> reconciliation status
  -> audit evidence package
  -> tax-reporting readiness output
  -> professional review
```

The sample workflow is a demonstration pattern. It is designed to support professional review and implementation planning, not to produce final tax filings or legal conclusions.

## Documentation Index

- [Architecture](docs/architecture.md)
- [FASB ASU 2023-08 Mapping](docs/fasb_asu_2023_08_mapping.md)
- [IRS Form 1099-DA Mapping Readiness](docs/irs_1099_da_mapping.md)
- [Form 8949 Reconciliation Support](docs/form_8949_reconciliation.md)
- [Audit Evidence Package](docs/audit_evidence_package.md)
- [Professional Review Scope](docs/professional_review_scope.md)
- [Roadmap](docs/roadmap.md)
- [Disclaimer](docs/disclaimer.md)

## Sample Files

- `sample_data/digital_asset_transactions.csv` - fake transaction source data.
- `sample_outputs/fair_value_records_sample.csv` - demonstration fair-value support records.
- `sample_outputs/journal_entries_sample.csv` - demonstration ERP journal-entry preparation rows.
- `sample_outputs/form_8949_reconciliation_sample.csv` - demonstration reconciliation support rows.
- `sample_outputs/audit_evidence_package_summary.md` - example reviewer-facing evidence summary.
- `examples/sample_workflow.md` - concise end-to-end demonstration workflow.

## Roadmap

- **Phase 1: Documentation and reference implementation.** Maintain the Odoo transaction-sync reference module, public documentation, sample data, and conservative standards mapping.
- **Phase 2: Accounting core and fair-value mapping.** Add structured fair-value records, valuation-source traceability, cost-basis methods, and journal-entry preparation logic.
- **Phase 3: Audit evidence and tax-reporting readiness.** Add reviewable evidence exports, reconciliation status tracking, 1099-DA field-mapping readiness, and Form 8949 reconciliation support.
- **Phase 4: Portability and practitioner feedback.** Improve portability across ERP deployments and incorporate feedback from Odoo implementers, CPAs, tax preparers, and technical reviewers.

## Professional Review Requirement

This repository provides technical reference materials only. Any accounting, tax, audit, legal, security, or regulatory use requires review by qualified professionals. Demonstration outputs should be treated as working papers or support schedules subject to validation, not as final returns, filings, opinions, or certifications.
