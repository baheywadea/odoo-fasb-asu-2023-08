# Odoo FASB ASU 2023-08 Digital Asset Compliance Framework

**Open-source ERP compliance infrastructure for automating digital asset accounting, fair-value tracking, and audit-ready reporting inside Odoo.**

![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)
![Odoo Version](https://img.shields.io/badge/Odoo-19.0-8A2BE2)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

---

## What This Project Is — And Is Not

> This section exists to be unambiguous. Please read it before evaluating the project.

### ✅ This project IS:

- **ERP accounting automation** — automated journal entries, fair-value remeasurement, and period-end disclosure inside Odoo
- **Compliance infrastructure** — supporting FASB ASU 2023-08 reporting workflows for U.S. SMEs
- **Non-custodial** — no funds are held, moved, or controlled at any point
- **Read-only** — transaction data is ingested via read-only API connections; no write access to external accounts
- **Financial reporting tooling** — the output is accounting records and disclosure schedules, not financial transactions

### ❌ This project is NOT:

- A cryptocurrency exchange
- A trading platform or investment tool
- A custodial wallet or fund manager
- A money transmission service
- A payment processor
- An investment advisory product

---

## The Problem: FASB ASU 2023-08 Creates an ERP Accounting Burden

**FASB Accounting Standards Update 2023-08** — *Accounting for and Disclosure of Crypto Assets* — is effective for fiscal years beginning after **December 15, 2024**, with early adoption permitted.

For businesses holding qualifying digital assets, the standard requires:

- **Fair-value measurement** at each reporting date, replacing the previous indefinite-lived intangible asset model
- **Unrealized gains and losses** recognized in net income each period
- **Enhanced tabular disclosures** covering cost basis, fair value, unrealized gain/loss, restrictions, and significant holdings
- **IRS Form 8949-ready tax lot records** for realized dispositions

For most U.S. SMEs, this creates a real operational problem: their ERP or accounting software has no built-in mechanism to capture daily fair values, auto-generate the required journal entries, or produce structured disclosure schedules. Many lack an affordable, ERP-integrated path to meet these requirements without expensive custom development or manual spreadsheet workflows.

---

## The ERP Compliance Gap

| Platform | Native Digital Asset Accounting | Fair-Value Automation | ASU 2023-08 Disclosure Output | SME-Accessible |
|---|---|---|---|---|
| SAP S/4HANA | ❌ Requires custom dev | ❌ | ❌ | ❌ Enterprise pricing |
| Oracle NetSuite | ❌ Requires custom dev | ❌ | ❌ | ⚠️ Mid-market pricing |
| Microsoft Dynamics 365 | ❌ Requires custom dev | ❌ | ❌ | ⚠️ Mid-market pricing |
| Odoo Community (unmodified) | ❌ No native support | ❌ | ❌ | ✅ Open-source |
| **This Framework (Odoo)** | ✅ Automated | ✅ Automated | ✅ Structured output | ✅ Free, open-source |

---

## The Solution: Three-Layer Compliance Architecture

### Layer 1 — ERP-Payment Integration Layer (`crypto_payment_sync`)

Connects Odoo to digital asset payment processors and exchange data providers via **read-only API polling and webhooks**. Ingests confirmed transaction records — amount, timestamp, asset type, counterparty reference — and maps them to Odoo accounting journals and analytic accounts. No write access to external systems. No fund movement.

**What it handles:**
- Read-only API credential management (per provider)
- Webhook receiver for incoming transaction events
- Transaction deduplication and reconciliation queue
- Mapping to Odoo journal entries, currencies, and accounting accounts

### Layer 2 — Automated Compliance Engine (`fasb_compliance_engine`)

Implements the core FASB ASU 2023-08 accounting logic inside Odoo's standard accounting framework.

**What it handles:**
- Fair-value capture at transaction date and at each reporting period end
- Automated unrealized gain/loss journal entries (mark-to-market remeasurement)
- Tax lot tracking using configurable cost-basis methods (FIFO, specific identification)
- Period-end remeasurement wizard for batch processing
- Realized gain/loss calculation on disposition events

### Layer 3 — Reporting & Disclosure Layer (`digital_asset_reporting`)

Generates structured, auditor-ready output directly from Odoo's accounting data — no manual exports or off-system spreadsheets required.

**What it handles:**
- FASB ASU 2023-08 tabular disclosure schedule (cost basis, fair value, unrealized G/L, restrictions)
- IRS Form 8949-ready realized gain/loss report
- Period-over-period digital asset roll-forward
- Audit trail with timestamped fair-value source records
- Export to PDF and Excel for CPA review

---

## Production Background

This framework is built on **production-validated ERP architecture patterns** developed across active Odoo deployments spanning multiple industries and countries, including:

- Payment gateway integrations (K-Net, MyFatoorah, Visa/Mastercard CyberSource, DHL Logistics API)
- API polling and webhook-based transaction ingestion
- Automated multi-currency accounting and cross-border reconciliation
- Deferred revenue recognition and contract automation
- Audit-ready financial workflows with full journal entry traceability

> **Important:** The architecture patterns are production-validated. The open-source modules in this repository are **under active development** and should not be used in production accounting environments without qualified CPA and technical review. See the [Compliance Disclaimer](#compliance-disclaimer) below.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              EXTERNAL DIGITAL ASSET PROVIDERS               │
│   (Payment Processors · Exchange Data APIs · Blockchain)    │
└──────────────────────────┬──────────────────────────────────┘
                           │  Read-Only API / Webhooks
                           │  (no fund movement, no writes)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1 — INTEGRATION MIDDLEWARE               │
│                   crypto_payment_sync                       │
│  · API credential management (read-only)                    │
│  · Webhook receiver & transaction ingestion                 │
│  · Deduplication & reconciliation queue                     │
│  · Odoo journal / account mapping                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              LAYER 2 — FASB COMPLIANCE ENGINE               │
│                  fasb_compliance_engine                     │
│  · Fair-value capture (transaction date + period end)       │
│  · Unrealized gain/loss remeasurement (ASU 2023-08)         │
│  · Tax lot tracking (FIFO / specific identification)        │
│  · Period-end remeasurement wizard                          │
│  · Realized gain/loss on disposition                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           LAYER 3 — REPORTING & DISCLOSURE                  │
│                 digital_asset_reporting                     │
│  · FASB ASU 2023-08 tabular disclosure schedule             │
│  · IRS Form 8949-ready realized gain/loss report            │
│  · Digital asset roll-forward by period                     │
│  · Audit trail with fair-value source records               │
│  · PDF / Excel export for CPA review                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  ODOO ERP ACCOUNTING                        │
│  Standard Odoo journal entries · Chart of accounts          │
│  Multi-currency ledger · Financial statements               │
└─────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
odoo-fasb-asu-2023-08/
│
├── crypto_payment_sync/          # Layer 1: Read-only API integration & transaction ingestion
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

> ⚠️ **This project is under active development. Installation steps may change before the first stable release. Do not use in a production accounting environment without qualified technical and CPA review.**

### Prerequisites

- Odoo 19.0 Community or Enterprise
- Python 3.10+
- PostgreSQL 14+

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/baheywadea/odoo-fasb-asu-2023-08.git

# 2. Copy addons to your Odoo custom addons path
cp -r odoo-fasb-asu-2023-08/crypto_payment_sync /your/odoo/addons/
cp -r odoo-fasb-asu-2023-08/fasb_compliance_engine /your/odoo/addons/
cp -r odoo-fasb-asu-2023-08/digital_asset_reporting /your/odoo/addons/

# 3. Restart Odoo
sudo systemctl restart odoo   # or your equivalent

# 4. In Odoo: Settings → Activate Developer Mode → Apps → Update App List

# 5. Search for and install:
#    - Digital Asset Sync (crypto_payment_sync)
#    - FASB Compliance Engine (fasb_compliance_engine)
#    - Digital Asset Reporting (digital_asset_reporting)

# 6. Configure:
#    - Settings → Digital Assets: enter read-only API credentials per provider
#    - Accounting → Configuration: map digital asset accounts to your chart of accounts
#    - Set your default cost-basis method (FIFO recommended for U.S. GAAP)
```

---

## Roadmap

- [x] Architecture design and documentation
- [x] Production prototype pattern validated (payment gateway integrations, automated accounting, API ingestion)
- [ ] `crypto_payment_sync` — read-only API integration layer
- [ ] `fasb_compliance_engine` — fair-value accounting and ASU 2023-08 logic
- [ ] `digital_asset_reporting` — disclosure reports and audit-ready export
- [ ] Demo database with sample data
- [ ] UI screenshots
- [ ] Walkthrough video
- [ ] Odoo Apps Marketplace listing
- [ ] Pilot feedback from SMEs, CPA firms, and Odoo partners

---

## Who This Is For

| Audience | Relevance |
|---|---|
| **Odoo partners serving U.S. clients** | Add ASU 2023-08 compliance capability to your service offering |
| **U.S. SMEs holding or receiving digital assets** | Automate fair-value accounting and disclosure inside your existing Odoo ERP |
| **CPA firms** | Provide clients with structured, auditor-ready digital asset reports from their ERP |
| **Fintech and payment teams** | Add GAAP-compliant accounting automation to digital asset payment workflows |
| **Accounting technology builders** | Extend or integrate with a structured open-source compliance layer |
| **Odoo ERP developers** | Contribute to an ERP compliance framework in an emerging accounting domain |

---

## Screenshots / Demo

**Coming soon:**

- Odoo crypto transaction import screen
- Fair-value capture and price source configuration
- Automated journal entry generation
- Period-end remeasurement wizard
- FASB ASU 2023-08 tabular disclosure report output
- IRS Form 8949-ready gain/loss export

---

## Compliance Disclaimer

This project is provided for **technical and educational purposes only**.

It is **not** legal advice, accounting advice, tax advice, investment advice, financial advice, custody services, or money transmission services of any kind.

FASB ASU 2023-08 compliance requirements vary by entity type, fiscal year, asset classification, and jurisdiction. The accounting logic implemented in this framework reflects a technical interpretation of the published standard and has not been reviewed or approved by FASB, the AICPA, the SEC, or any regulatory authority.

**Businesses should consult qualified CPAs, tax advisors, legal counsel, and compliance professionals before implementing any digital asset accounting workflow.**

This software is provided "as is," without warranty of any kind. See the [LICENSE](LICENSE) file for full terms.

---

## Developer

**Bahey Wadea Zakary Hakim**
Senior ERP Architect | Odoo Specialist | Financial Automation Engineer

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
- **SME owners** holding or receiving digital assets in their business operations
- **Odoo and Python developers** interested in ERP compliance tooling

To contribute, open an issue or pull request on GitHub. For pilot feedback or collaboration inquiries, reach out via email.

---

## License

**GNU Lesser General Public License v3.0 (LGPL-3)**

This project is free and open-source software. You may use, modify, and distribute it under the terms of the LGPL-3 license. See the [LICENSE](LICENSE) file for full details.

---

*This README was last updated: 2026*
