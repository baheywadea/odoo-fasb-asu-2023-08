# Odoo FASB ASU 2023-08 Digital Asset Compliance Framework

**Open-source ERP compliance infrastructure for automating digital asset accounting, fair-value tracking, and audit-ready reporting inside Odoo.**

![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)
![Odoo Version](https://img.shields.io/badge/Odoo-19.0-8A2BE2)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

---

## Important: What This Project Is — And Is Not

This section exists to be unambiguous. Please read it before evaluating the project.

### This project is primarily:

- **ERP accounting automation** — automated journal entries, fair-value remeasurement, and disclosure reporting inside Odoo
- **Digital asset transaction record ingestion** — receiving and normalizing transaction data from external providers into the Odoo accounting ledger
- **Fair-value tracking** — capturing asset prices at transaction date and at each reporting period end
- **Audit-ready reporting** — structured disclosure schedules and cost-basis records designed for CPA and auditor review
- **Compliance-supporting infrastructure** — tools to help businesses work toward FASB ASU 2023-08 reporting requirements inside their existing Odoo ERP

### This project is NOT:

- A cryptocurrency exchange
- A trading platform or investment product
- A custodial wallet service
- A money transmission business
- A regulated financial intermediary of any kind

### Regarding advanced implementation components:

This repository may contain code related to wallet management, transaction signing, or outbound payment workflows. **These are optional advanced implementation components.** They are not required for the core FASB ASU 2023-08 compliance workflow and must be evaluated separately for legal, tax, accounting, regulatory, and security compliance before any production use. Enabling these features may create legal or regulatory obligations depending on your jurisdiction and business model. Consult qualified legal and compliance professionals before use.

---

## The Problem: FASB ASU 2023-08 Creates an ERP Accounting Burden

**FASB Accounting Standards Update 2023-08** — *Accounting for and Disclosure of Crypto Assets* — is effective for fiscal years beginning after **December 15, 2024**, with early adoption permitted.

For businesses holding qualifying digital assets, the standard requires:

- **Fair-value measurement** at each reporting date, replacing the previous indefinite-lived intangible asset model
- **Unrealized gains and losses** recognized in net income each period — not just on disposal
- **Enhanced tabular disclosures** covering cost basis, fair value, unrealized gain/loss, restrictions, and significant holdings
- **Structured cost-basis records** supporting IRS Form 8949 reporting for realized dispositions

For most U.S. SMEs, this creates a practical operational problem: their ERP or accounting software has no built-in mechanism to capture daily fair values, auto-generate the required journal entries, or produce structured disclosure schedules. Many U.S. SMEs lack an affordable, ERP-integrated path to meet these requirements without expensive custom development or error-prone manual spreadsheet workflows.

---

## The ERP Compliance Gap

| Platform | Native Digital Asset Accounting Automation | Typical Gap |
|---|---|---|
| SAP S/4HANA | Limited / custom | Requires specialized configuration or custom development |
| Oracle NetSuite | Limited / custom | Often requires SuiteScript or third-party tooling |
| Microsoft Dynamics 365 | Limited / custom | No standard SME-focused digital asset accounting workflow |
| Odoo Community | Not available by default | No official open-source FASB ASU 2023-08 workflow |
| **This Framework** | **Open-source / Odoo-focused** | Designed to support transaction ingestion, fair-value tracking, journal automation, and disclosure workflows |

---

## The Solution: Three-Layer Compliance Architecture

### Layer 1 — Transaction Data Integration (`crypto_payment_sync`)

Middleware connecting Odoo to digital asset payment and transaction-data providers, with a core focus on transaction ingestion, reconciliation, accounting traceability, and compliance automation.

**What it handles:**
- Read-only API polling and webhook ingestion of confirmed transaction records
- Transaction normalization: amount, timestamp, asset type, provider reference
- Deduplication and reconciliation queue
- Mapping to Odoo journal accounts, currencies, and analytic dimensions
- No fund custody required for the core compliance workflow

### Layer 2 — Automated Compliance Engine (`fasb_compliance_engine`)

Implements FASB ASU 2023-08 accounting logic inside Odoo's standard accounting framework. Helps automate the period-end workflows that the standard requires.

**What it handles:**
- Fair-value capture at transaction date and reporting period end
- Automated unrealized gain/loss journal entry preparation (mark-to-market remeasurement)
- Tax lot tracking using configurable cost-basis methods (FIFO, specific identification)
- Period-end remeasurement wizard for batch processing
- Realized gain/loss calculation on disposition events
- Full audit trail with timestamped price source records

### Layer 3 — Reporting & Disclosure (`digital_asset_reporting`)

Generates structured, auditor-ready output directly from Odoo's accounting data — designed to support CPA and auditor review without requiring manual exports or off-system spreadsheets.

**What it handles:**
- FASB ASU 2023-08 tabular disclosure schedule (cost basis, fair value, unrealized G/L, restrictions)
- IRS Form 8949-ready realized gain/loss report
- Digital asset roll-forward by period
- Audit trail export with fair-value source documentation
- PDF and Excel output for accountant review

---

## Core vs. Optional Advanced Capabilities

### Core Accounting-Focused Capabilities

These capabilities support the primary FASB ASU 2023-08 compliance workflow and are the focus of this project:

- Digital asset transaction import and reconciliation
- Webhook and API polling from transaction-data providers
- Provider transaction references and accounting traceability
- Fair-value tracking and period-end remeasurement
- Automated journal entry preparation
- Audit trail generation
- FASB ASU 2023-08 disclosure schedule output
- Cost-basis records and IRS Form 8949-ready reporting support

### Optional Advanced Capabilities

The following capabilities may be present in the codebase as implementation components but are **not required** for the core compliance workflow:

- HD wallet management
- WalletConnect checkout integration
- EVM transaction signing
- Vendor and employee crypto payout workflows
- Outbound crypto payment execution

> **Important:** Optional advanced capabilities must be enabled only after proper legal, accounting, regulatory, and security review. Enabling outbound payment or signing features may create custody, money transmission, or other regulatory obligations in your jurisdiction. This project does not provide guidance on those obligations — consult qualified legal and compliance professionals before enabling these features.

---

## Production Background

`crypto_payment_sync` is based on production-validated architecture patterns involving digital asset transaction detection, webhook processing, exchange-rate capture, accounting references, and audit-trail generation — developed across active ERP deployments spanning multiple industries and jurisdictions.

Some advanced payment-execution features may exist in the codebase. The primary purpose of this repository is **accounting automation and compliance support**, not custody, exchange, or money transmission.

> **Note:** The open-source modules in this repository are **under active development** and should not be used in production accounting environments without qualified CPA and technical review.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│         EXTERNAL DIGITAL ASSET / TRANSACTION PROVIDERS      │
│    (Payment Processors · Exchange Data APIs · Blockchain)   │
└──────────────────────────┬──────────────────────────────────┘
                           │  Read-Only APIs / Webhooks
                           │  (transaction data ingestion only)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 1 — TRANSACTION DATA INTEGRATION            │
│                    crypto_payment_sync                      │
│  · Webhook receiver & API polling                           │
│  · Transaction normalization & deduplication                │
│  · Reconciliation queue                                     │
│  · Odoo journal / account mapping                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 2 — FASB ASU 2023-08 COMPLIANCE ENGINE      │
│                   fasb_compliance_engine                    │
│  · Fair-value capture (transaction date + period end)       │
│  · Unrealized gain/loss remeasurement journal prep          │
│  · Tax lot tracking (FIFO / specific identification)        │
│  · Period-end remeasurement wizard                          │
│  · Realized gain/loss on disposition events                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 3 — REPORTING & DISCLOSURE               │
│                  digital_asset_reporting                    │
│  · FASB ASU 2023-08 tabular disclosure schedule             │
│  · IRS Form 8949-ready realized gain/loss report            │
│  · Period-over-period digital asset roll-forward            │
│  · Audit trail with fair-value source records               │
│  · PDF / Excel export for CPA and auditor review            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    ODOO ERP ACCOUNTING                      │
│   Standard journal entries · Chart of accounts              │
│   Multi-currency ledger · Financial statements              │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
odoo-fasb-asu-2023-08/
│
├── crypto_payment_sync/          # Layer 1: Transaction data integration & ingestion
│   ├── models/
│   ├── views/
│   ├── data/
│   └── __manifest__.py
│
├── fasb_compliance_engine/       # Layer 2: Fair-value accounting & ASU 2023-08 logic
│   ├── models/
│   ├── wizard/
│   ├── views/
│   └── __manifest__.py
│
├── digital_asset_reporting/      # Layer 3: Disclosure reports & audit-ready export
│   ├── models/
│   ├── report/
│   ├── views/
│   └── __manifest__.py
│
├── docs/                         # Architecture documentation & implementation guides
│
└── README.md
```

---

## Installation — Development Preview

> ⚠️ **This project is under active development. Installation steps may change before the first stable release. Do not deploy in a production accounting environment without qualified technical and CPA review.**

### Prerequisites

- Odoo 17.0 Community or Enterprise
- Python 3.10+
- PostgreSQL 14+

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/baheywadea/odoo-fasb-asu-2023-08.git

# 2. Copy module folders to your Odoo custom addons path
cp -r odoo-fasb-asu-2023-08/crypto_payment_sync /your/odoo/addons/
cp -r odoo-fasb-asu-2023-08/fasb_compliance_engine /your/odoo/addons/
cp -r odoo-fasb-asu-2023-08/digital_asset_reporting /your/odoo/addons/

# 3. Restart Odoo
sudo systemctl restart odoo   # or your equivalent startup command

# 4. In Odoo: Settings → Activate Developer Mode → Apps → Update App List

# 5. Search for and install:
#    - Digital Asset Sync        (crypto_payment_sync)
#    - FASB Compliance Engine    (fasb_compliance_engine)
#    - Digital Asset Reporting   (digital_asset_reporting)

# 6. Configure:
#    - Accounting → Configuration: map digital asset accounts to your chart of accounts
#    - Set your default cost-basis method (FIFO recommended for U.S. GAAP)
#    - Configure provider credentials only as needed for transaction ingestion
```

> Optional advanced features (wallet, signing, outbound payments) are disabled by default and require separate configuration and professional review before enabling.

---

## Regulatory Context

This framework is designed to help support the following regulatory and reporting frameworks. "Supports" and "helps prepare" are used intentionally — this software does not guarantee compliance with any regulation.

| Regulation / Guidance | Compliance Area Supported |
|---|---|
| FASB ASU 2023-08 | Fair-value measurement and disclosure support for qualifying crypto assets |
| ASC 820 | Fair-value measurement reference framework for price sourcing |
| IRS Form 8949 | Cost-basis and disposal reporting support |
| IRS digital asset reporting rules | Transaction record and reporting workflow support |
| NIST CSF 2.0 | Security control alignment for credential handling and audit logging |
| SBA modernization priorities | SME access to affordable technology and financial transparency tooling |

---

## Roadmap

- [x] Architecture design and documentation
- [x] Production-validated transaction ingestion and accounting patterns
- [ ] `crypto_payment_sync` — transaction data integration layer
- [ ] `fasb_compliance_engine` — fair-value accounting and ASU 2023-08 logic
- [ ] `digital_asset_reporting` — disclosure reports and audit-ready export
- [ ] Tax lot tracking and IRS Form 8949-ready output
- [ ] Journal entry automation
- [ ] Demo database with sample data
- [ ] UI screenshots
- [ ] Walkthrough video
- [ ] CPA firm and Odoo partner pilot feedback
- [ ] Optional advanced payment features — reviewed separately with appropriate professional guidance

---

## Who This Is For

| Audience | Relevance |
|---|---|
| **Odoo partners serving U.S. clients** | Add ASU 2023-08 compliance capability to your service offering |
| **U.S. SMEs holding or receiving digital assets** | Automate fair-value accounting and disclosure inside your existing Odoo ERP |
| **CPA firms** | Provide clients with structured, auditor-ready digital asset reports generated from their ERP |
| **Fintech ERP teams** | Add GAAP-aligned accounting automation to digital asset payment ingestion workflows |
| **ERP developers** | Contribute to a structured open-source compliance layer in an emerging accounting domain |
| **Accounting technology builders** | Extend or integrate with a modular, Odoo-native compliance framework |

---

## Screenshots / Demo

**Coming soon:**

- Odoo digital asset transaction import screen
- Fair-value capture and price source configuration
- Automated journal entry draft
- Period-end remeasurement wizard
- FASB ASU 2023-08 tabular disclosure report output
- IRS Form 8949-ready gain/loss export

---

## Compliance Disclaimer

This software is provided for **technical and educational purposes only**.

It does not provide:

- Legal advice
- Accounting advice
- Tax advice
- Investment advice
- Custody services
- Money transmission services
- Financial advice of any kind

Use of optional advanced features — including any wallet management, transaction signing, or outbound payment functionality — may create legal or regulatory obligations depending on jurisdiction, business model, and implementation details. This project does not assess, address, or accept responsibility for those obligations.

The accounting logic implemented in this framework reflects a technical interpretation of published standards and guidance. It has not been reviewed or approved by FASB, the AICPA, the IRS, the SEC, or any regulatory authority.

**Businesses should consult qualified CPAs, tax advisors, legal counsel, and compliance professionals before implementing any digital asset accounting workflow in a production environment.**

This software is provided "as is," without warranty of any kind. See the [LICENSE](LICENSE) file for full terms.

---

## Developer

**Bahey Wadea Zakary Hakim**
Senior ERP Architect | Odoo Specialist | Financial Automation Engineer

13+ years of software engineering experience, including production ERP deployments supporting businesses across Kuwait and international operations involving U.S., U.K., Egypt, Saudi Arabia, and European contexts. Specialized in financial compliance automation, payment gateway integration, multi-currency ERP systems, and audit-ready accounting workflows.

| | |
|---|---|
| Website | [baheywadea.com](https://baheywadea.com) |
| LinkedIn | [linkedin.com/in/baheywadeahakim](https://linkedin.com/in/baheywadeahakim) |
| GitHub | [github.com/baheywadea](https://github.com/baheywadea) |
| Odoo Marketplace | [Published Modules](https://apps.odoo.com/apps/modules/browse?search=bahey+wadea) |
| Email | [bahey.wadea@gmail.com](mailto:bahey.wadea@gmail.com) |

---

## Contributing

Contributions, issue reports, and pilot feedback are welcome from:

- **Odoo partners** implementing digital asset workflows for U.S. clients
- **CPA firms** with experience in ASU 2023-08 client engagements
- **SME owners** holding or receiving digital assets in business operations
- **Fintech ERP teams** integrating payment data into accounting systems
- **Odoo and Python developers** interested in ERP compliance tooling

Contributions related to compliance logic, disclosure formats, or tax reporting should be reviewed by qualified accounting and tax professionals before being merged. Open an issue to discuss before submitting a pull request on compliance-sensitive components.

To get involved, open an issue or pull request on GitHub. For pilot feedback or collaboration inquiries, reach out via email.

---

## License

**GNU Lesser General Public License v3.0 (LGPL-3)**

This project is free and open-source software. You may use, modify, and distribute it under the terms of the LGPL-3 license. See the [LICENSE](LICENSE) file for full details.

---

## Professional Feedback Requested

I am currently collecting professional feedback from Odoo developers, ERP consultants, accountants, CPAs, fintech professionals, and digital asset compliance specialists.

Please share your feedback here:

https://github.com/baheywadea/odoo-fasb-asu-2023-08/discussions/2

*README last updated: 2026*
