# Odoo FASB ASU 2023-08 — Digital Asset Compliance Framework

> **Free, open-source FASB ASU 2023-08 compliance infrastructure for U.S. small and medium-sized enterprises (SMEs), built on Odoo ERP.**

[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo Version](https://img.shields.io/badge/Odoo-19.0+-875A7B)](https://www.odoo.com)
[![Status](https://img.shields.io/badge/Status-Active%20Development-green)](https://github.com/baheywadea/odoo-fasb-asu-2023-08)
[![U.S. Compliance](https://img.shields.io/badge/Standard-FASB%20ASU%202023--08-red)](https://fasb.org)

---

## The Problem

**FASB Accounting Standards Update 2023-08** (*Intangibles—Goodwill and Other—Crypto Assets, Subtopic 350-60*) became effective for fiscal years beginning after **December 15, 2024**.

It requires U.S. businesses holding or transacting in digital assets to:

- Measure digital assets at **fair value** each reporting period
- Recognize **unrealized gains and losses** immediately in net income
- Maintain enhanced **disclosure requirements**
- Generate **IRS Form 8949-ready** cost basis reporting

### The Gap

| Platform | Native FASB ASU 2023-08 Support | Cost |
|---|---|---|
| SAP S/4HANA | ❌ Requires custom ABAP development | $100,000+ |
| Oracle NetSuite | ❌ Requires SuiteScript customization | $50,000–$150,000 |
| Microsoft Dynamics 365 | ❌ No native digital asset accounting | $80,000+ |
| Odoo (community) | ❌ No official compliance module | — |
| **This Framework** | ✅ Free. Open-source. SME-ready. | **$0** |

**34.8 million U.S. SMEs** — representing 99.9% of American businesses — currently have no affordable, automated path to FASB ASU 2023-08 compliance.

---

## The Solution

A **modular open-source framework** that integrates directly into Odoo ERP, providing full FASB ASU 2023-08 compliance automation at zero licensing cost.

### Component 1 — ERP-Payment Integration Layer (`crypto_payment_sync`)

Production-grade middleware connecting Odoo to regulated digital payment APIs across **13+ blockchain networks**:

| Blockchain | Symbol | Type |
|---|---|---|
| Ethereum | ETH | L1 |
| Bitcoin | BTC | L1 |
| BNB Smart Chain | BNB | L1 |
| Polygon | MATIC | L2 |
| Avalanche | AVAX | L1 |
| Solana | SOL | L1 |
| Tron | TRX | L1 |
| Litecoin | LTC | L1 |
| Optimism | OP | L2 |
| Arbitrum One | ARB | L2 |
| Base | BASE | L2 |
| + 2 more | — | — |

**Key capabilities (all currently implemented):**

- **HD Wallet Management (BIP-32/BIP-44)** — hierarchical deterministic wallet derivation; private keys never leave the Odoo server
- **Address-Per-Transaction Model** — every payment receives a unique blockchain address, eliminating misattribution risk
- **Real-Time Webhook Subscriptions** — CryptoAPIs.io integration; payments confirmed on-chain trigger automatic ERP finalization without polling
- **EVM Transaction Signing & Broadcasting** — outbound crypto payments signed locally, broadcast via CryptoAPIs
- **WalletConnect v2 Integration** — customers connect MetaMask, Trust Wallet, or any WC2-compatible wallet directly at checkout
- **Multi-Currency Sync** — full asset catalog synced into Odoo `res.currency` with live exchange rates via CryptoAPIs market data
- **Partner Crypto Address Book** (`res.partner.crypto.address`) — per-partner external address storage scoped by blockchain and network
- **Vendor & Employee Crypto Payouts** — outbound `account.payment` triggers real on-chain transfers to suppliers and employees
- **Audit-Complete Journal Entries** — all inbound and outbound crypto flows post through standard Odoo `account.move` for full audit trail

### Component 2 — FASB Compliance Engine (`fasb_compliance_engine`)

*Active development — targeting Q3 2026 release*

Zero-manual-intervention FASB ASU 2023-08 accounting automation built on top of the production payment layer:

- Automatic fair value remeasurement at each reporting period-end
- Unrealized gain/loss recognition in net income (per ASU 2023-08 §350-60-35)
- Real-time exchange rate capture at transaction time (basis establishment)
- Blockchain transaction reconciliation against Odoo accounting ledgers
- Compliance audit trail with on-chain transaction references

### Component 3 — Digital Asset Reporting (`digital_asset_reporting`)

*Active development — targeting Q3 2026 release*

- IRS Form 8949-ready cost basis reporting (per-asset, per-transaction)
- FASB ASU 2023-08 disclosure report (fair value hierarchy, concentration risk)
- Period-end remeasurement summary for external auditors

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ODOO ERP CORE                            │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │  Accounting │    │  Payment     │    │   Reporting       │  │
│  │   Module    │    │  Module      │    │   Module          │  │
│  └──────┬──────┘    └──────┬───────┘    └────────┬──────────┘  │
│         └──────────────────┴────────────────────┘              │
│                            │                                    │
│              ┌─────────────▼──────────────┐                    │
│              │   FASB Compliance Engine    │  ← Component 2     │
│              │   - Fair Value Tracker      │                    │
│              │   - Journal Automation      │                    │
│              │   - Gain/Loss Recognition   │                    │
│              │   - IRS 8949 Reporting      │                    │
│              └─────────────┬──────────────┘                    │
│                            │                                    │
│         ┌──────────────────┴───────────────────┐               │
│         │     Crypto Payment Sync Layer         │  ← Component 1│
│         │  - HD Wallet (BIP-32/44)             │               │
│         │  - Address-Per-Transaction           │               │
│         │  - Webhook Handler                   │               │
│         │  - EVM Signing & Broadcast           │               │
│         │  - WalletConnect v2                  │               │
│         │  - Multi-currency Sync               │               │
│         └──────────────────┬───────────────────┘               │
└────────────────────────────┼────────────────────────────────────┘
                             │
           ┌─────────────────┼──────────────────┐
           │                 │                  │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │  Coinbase   │   │   BitPay /  │   │  CoinGate   │
    │  Commerce   │   │  BTCPay     │   │  + Others   │
    └─────────────┘   └─────────────┘   └─────────────┘
```

### Core Data Models

```
payment.provider          ← extends Odoo's native payment provider
    └── crypto.wallet         ← HD wallet with xpub + mnemonic
            └── crypto.wallet.address       ← derived address per transaction
                    └── crypto.wallet.address.event  ← webhook subscription
                    └── crypto.transaction.evm        ← on-chain tx record

res.partner
    └── res.partner.crypto.address   ← partner external crypto addresses

account.payment           ← extended: outbound crypto transfers
account.journal           ← flagged as crypto journal (is_crypto)
res.currency              ← extended: crypto type + CryptoAPIs referenceId
```

---

## Production Background

**This framework is not a research prototype.**

Component 1 (`crypto_payment_sync`) is built on a fully operational production deployment currently running in a live commercial environment, including:

- Live blockchain transaction detection and webhook processing across multiple networks
- Automated journal entry generation with real-time exchange rate capture
- Complete audit trail generation linked to on-chain transaction hashes
- Multi-currency reconciliation across 13+ blockchain networks
- Outbound crypto payments to vendors and employees via ERP-native workflows

The proposed open-source release formalizes and publicly distributes this proven, deployed capability — making it freely available to U.S. SMEs that cannot afford enterprise-grade alternatives.

---

## U.S. Regulatory Context

This framework directly addresses mandatory U.S. compliance requirements:

| Regulation | Requirement Addressed |
|---|---|
| **FASB ASU 2023-08** | Fair-value accounting for digital assets — effective Dec 15, 2024 |
| **IRS Form 1099-DA** | Broker digital asset reporting — cost basis tracking |
| **IRS Form 8949** | Capital gains/losses reporting — per-transaction cost basis |
| **Bipartisan Infrastructure Law (2021)** | Digital asset broker reporting provisions |
| **SEC Digital Asset Guidance** | Audit trail and disclosure requirements |
| **SBA Modernization Priorities** | SME technology access and financial competitiveness |

FASB ASU 2023-08 is a **U.S.-specific accounting standard** with no direct equivalent in other jurisdictions. The compliance gap it creates is unique to U.S. businesses and represents an urgent, unmet infrastructure need for the 34.8 million SMEs that form the backbone of the American economy.

---

## Who This Is For

Any U.S. small or medium-sized business that:

- Accepts or holds cryptocurrency as part of business operations
- Must comply with FASB ASU 2023-08 (effective December 2024)
- Uses Odoo ERP or is evaluating it for financial operations
- Cannot afford $50,000–$200,000 in custom ERP compliance development
- Needs audit-ready financial statements that include digital asset disclosures

---

## Installation

### Requirements

```
Python packages:
    requests
    mnemonic
    bip32
    eth-account
    eth-utils
    qrcode[pil]

Odoo modules:
    account
    payment
    website_sale
```

### Setup

1. Install `crypto_payment_sync` module in Odoo
2. Go to **Payment Providers** → enable **Crypto Payment**
3. Enter your **CryptoAPIs API Key**
4. Run **Sync Currencies** to import the full asset catalog
5. Create a **Crypto Wallet** linked to your desired blockchain network
6. Run **Sync Addresses** or **Derive New Addresses**
7. Set `web.base.url` in System Parameters (required for webhook callbacks)

---

## API Endpoints

| Route | Method | Description |
|---|---|---|
| `/crypto/pay/<tx_id>` | GET | QR payment page (WalletConnect v2 + EIP-681) |
| `/crypto/qr/<tx_id>.png` | GET | EIP-681 QR code image |
| `/crypto/status/<tx_id>` | POST | Poll payment status |
| `/crypto/intent/<tx_id>` | POST | Get chain/address/amount for WalletConnect |
| `/crypto/wc_tx/<tx_id>` | POST | Store WalletConnect transaction hash |
| `/invoice_link/crypto/callback/<tx_id>` | POST | CryptoAPIs webhook receiver |

All public endpoints are protected by a per-transaction 32-byte URL-safe random token.

---

## Roadmap

| Milestone | Status |
|---|---|
| Architecture design and documentation | ✅ Complete |
| Production prototype — live deployment | ✅ Complete |
| `crypto_payment_sync` — full payment integration layer | ✅ Complete |
| HD wallet management (BIP-32/44) | ✅ Complete |
| Real-time webhook subscriptions (CryptoAPIs) | ✅ Complete |
| WalletConnect v2 checkout integration | ✅ Complete |
| Vendor & employee outbound crypto payments | ✅ Complete |
| Multi-currency sync with live exchange rates | ✅ Complete |
| `fasb_compliance_engine` — fair value remeasurement automation | 🔄 In Development |
| `digital_asset_reporting` — IRS Form 8949 report generation | 🔄 In Development |
| Community testing with U.S. SME beta users | 📅 Q3 2026 |
| Odoo Apps Marketplace — free community listing | 📅 Q3 2026 |
| Full documentation and implementation guide | 📅 Q3 2026 |

---

## Security

- Public payment pages protected by per-transaction random tokens (32-byte, URL-safe)
- EVM transaction signing performed locally — private keys never transmitted to third parties
- Address-per-transaction model prevents payment collision and improves on-chain privacy
- HD wallet architecture — extended public key (xpub) used for address derivation; private keys derived only at signing time

---

## Developer

**Bahey Wadea Zakary Hakim**
Senior ERP Architect & Enterprise Systems Developer

13+ years of production ERP deployments across Kuwait, Egypt, United Kingdom, Germany, and Czech Republic. Specialist in Odoo architecture, financial automation, regulatory compliance systems, and regulated payment API integrations for small and medium-sized enterprises.

- 🌐 [baheywadea.com](https://baheywadea.com)
- 💼 [LinkedIn](https://www.linkedin.com/in/baheywadeahakim/)
- 📦 [Odoo Marketplace](https://apps.odoo.com/apps/modules/browse?search=bahey+wadea)
- 📧 [bahey.wadea@gmail.com](mailto:bahey.wadea@gmail.com)

---

## Contributing

Contributions welcome — especially from U.S. SME owners, accountants, and Odoo developers who have encountered FASB ASU 2023-08 compliance challenges.

If you are a U.S.-based Odoo implementer or accounting professional interested in collaborating on the compliance engine or reporting modules, please open an issue describing your use case or area of expertise.

---

## License

**GNU Lesser General Public License v3.0 (LGPL-3)**

The same license used by Odoo Community Edition. Free to use, modify, and distribute.

---

*Built for the 34.8 million U.S. SMEs that need it.*
