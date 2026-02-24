# Odoo FASB ASU 2023-08 — Digital Asset Compliance Framework

> **Free, open-source FASB ASU 2023-08 compliance infrastructure for U.S. small and medium-sized enterprises (SMEs), built on Odoo ERP.**

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-17.0-875A7B)](https://www.odoo.com)
[![Status](https://img.shields.io/badge/Status-Active%20Development-green)]()

---

## The Problem

**FASB Accounting Standards Update 2023-08** (*Intangibles—Goodwill and Other—Crypto Assets, Subtopic 350-60*) became effective for fiscal years beginning after **December 15, 2024**.

It requires U.S. businesses holding or transacting in digital assets to:

- Measure digital assets at **fair value** each reporting period
- Recognize **unrealized gains and losses** immediately in net income
- Maintain enhanced **disclosure requirements**
- Generate **IRS Form 8949-ready** cost basis reporting

### The Gap

| Platform | Native FASB ASU 2023-08 Support |
|---|---|
| SAP S/4HANA | ❌ Requires $100,000+ custom ABAP development |
| Oracle NetSuite | ❌ Requires $50,000–$150,000 SuiteScript customization |
| Microsoft Dynamics 365 | ❌ No native digital asset accounting |
| Odoo (community) | ❌ No official compliance module |
| **This Framework** | ✅ Free. Open-source. SME-ready. |

**34.8 million U.S. SMEs** — representing 99.9% of American businesses — currently have no affordable, automated path to FASB ASU 2023-08 compliance.

---

## The Solution

A **three-component open-source framework** that integrates directly into Odoo ERP:

### Component 1 — ERP-Payment Integration Layer
Modular middleware connecting Odoo to regulated digital payment APIs:
- Coinbase Commerce
- BitPay / BTCPay Server
- CoinGate
- Extensible to any webhook-based payment processor

### Component 2 — Automated Compliance Engine
Zero-manual-intervention accounting automation:
- Real-time exchange rate capture at transaction time
- Automated journal entry generation (DR/CR)
- FASB ASU 2023-08 fair value remeasurement each reporting period
- Unrealized gain/loss tracking and recognition
- Blockchain transaction reconciliation
- IRS Form 8949-ready cost basis reporting

### Component 3 — Open-Source Distribution
- Released under LGPL-3 license
- Community-maintainable architecture
- Zero licensing cost for any U.S. SME
- Designed for Odoo 17.0, extensible to earlier versions

---

## Production Background

This framework is not a research project.

**Case Study: Live Digital Asset ERP Integration**

A fully operational production deployment of this exact architecture is currently running, including:

- Live blockchain transaction detection and webhook processing
- Automated journal entry generation with fair value tracking
- Real-time exchange rate capture via external API
- Complete audit trail generation
- Multi-currency reconciliation

The proposed open-source release is the formalization and public distribution of this proven, deployed capability.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     ODOO ERP CORE                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Accounting │  │   Inventory  │  │   Reporting       │  │
│  │   Module    │  │   Module     │  │   Module          │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         └────────────────┴──────────────────┘              │
│                          │                                  │
│              ┌───────────▼────────────┐                     │
│              │  FASB Compliance Core  │                     │
│              │  - Fair Value Engine   │                     │
│              │  - Journal Automation  │                     │
│              │  - Gain/Loss Tracker   │                     │
│              └───────────┬────────────┘                     │
│                          │                                  │
│         ┌────────────────┴─────────────────┐                │
│         │      Payment Integration Layer   │                │
│         │  - Webhook Handler               │                │
│         │  - Transaction Confirmation      │                │
│         │  - Exchange Rate API             │                │
│         └────────────────┬─────────────────┘                │
└──────────────────────────┼──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │   Coinbase  │  │    BitPay   │  │  CoinGate   │
   │   Commerce  │  │  BTCPay     │  │  + Others   │
   └─────────────┘  └─────────────┘  └─────────────┘
```

---

## Modules

```
odoo-fasb-asu-2023-08/
├── crypto_payment_sync/          # Payment API integration layer
│   ├── models/
│   │   ├── crypto_transaction.py
│   │   ├── exchange_rate.py
│   │   └── payment_provider.py
│   ├── controllers/
│   │   └── webhook.py
│   └── views/
├── fasb_compliance_engine/       # Core FASB accounting automation
│   ├── models/
│   │   ├── fair_value_tracker.py
│   │   ├── journal_automation.py
│   │   └── gain_loss_recognition.py
│   └── wizard/
│       └── period_remeasurement.py
├── digital_asset_reporting/      # IRS Form 8949 & disclosure reports
│   ├── models/
│   │   └── cost_basis_calculator.py
│   └── report/
│       ├── form_8949_report.py
│       └── fasb_disclosure_report.py
└── README.md
```

---

## Roadmap

- [x] Architecture design and documentation
- [x] Production prototype (live deployment)
- [ ] `crypto_payment_sync` — Coinbase Commerce webhook handler
- [ ] `fasb_compliance_engine` — Fair value remeasurement automation
- [ ] `digital_asset_reporting` — IRS Form 8949 report generation
- [ ] Community testing with U.S. SME beta users
- [ ] Odoo Apps Marketplace — free community listing
- [ ] Documentation and implementation guide

---

## Who This Is For

Any U.S. small or medium-sized business that:

- Accepts cryptocurrency payments
- Holds digital assets on the balance sheet
- Must comply with FASB ASU 2023-08
- Uses Odoo ERP (or is considering it)
- Cannot afford $50,000–$200,000 in custom development

---

## National Context

This framework directly addresses compliance requirements established by:

- **FASB ASU 2023-08** — mandatory fair-value accounting for digital assets
- **IRS Form 1099-DA** — broker digital asset reporting requirements
- **Bipartisan Infrastructure Law (2021)** — digital asset reporting provisions
- **SBA modernization priorities** — SME technology access and competitiveness

---

## Developer

**Bahey Wadea Zakary Hakim**
Senior ERP Developer & Enterprise Systems Architect

13+ years of production ERP deployments across Kuwait, Egypt, United Kingdom, Germany, and Czech Republic. Specialist in Odoo architecture, financial automation, and regulated payment API integrations.

- 🌐 [baheywadea.com](https://baheywadea.com)
- 💼 [LinkedIn](https://www.linkedin.com/in/baheywadeahakim/)
- 📦 [Odoo Marketplace](https://apps.odoo.com/apps/modules/browse?search=bahey+wadea)
- 📧 bahey.wadea@gmail.com

---

## Contributing

Contributions welcome. If you are a U.S. SME owner, accountant, or Odoo developer who has encountered FASB ASU 2023-08 compliance challenges, please open an issue describing your use case.

---

## License

This project is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3)** — the same license used by Odoo Community Edition.

You are free to use, modify, and distribute this software at no cost.

---

*Built for the 34.8 million U.S. SMEs that need it.*
