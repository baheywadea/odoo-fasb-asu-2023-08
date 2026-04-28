# Odoo FASB ASU 2023-08 — Digital Asset Compliance Framework

> Open-source ERP compliance infrastructure for automating digital asset accounting, fair-value tracking, and audit-ready reporting inside Odoo.

![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)
![Odoo Version](https://img.shields.io/badge/Odoo-17.0-purple.svg)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange.svg)

---

## Important Positioning

This project is an **ERP accounting and compliance automation framework**.

It is **not**:

- a crypto exchange
- a trading platform
- a custodial wallet
- a money transmission service
- a speculative crypto product

The framework is designed to operate as a **non-custodial, read-only accounting integration layer** that helps businesses connect digital asset transaction records to audit-ready ERP accounting workflows.

---

## The Problem

FASB Accounting Standards Update 2023-08 — *Intangibles—Goodwill and Other—Crypto Assets (Subtopic 350-60)* — became effective for fiscal years beginning after December 15, 2024.

It requires U.S. businesses holding qualifying digital assets to:

- measure crypto assets at fair value each reporting period
- recognize unrealized gains and losses in net income
- maintain enhanced disclosure requirements
- preserve audit-ready records of valuation and accounting treatment
- support tax-basis tracking and disposal reporting workflows

For many small and medium-sized businesses, this creates a practical ERP problem:

> Digital asset activity often exists outside the accounting system, while financial reporting obligations must be recorded inside the ERP.

Without automation, businesses may rely on spreadsheets, manual exchange-rate lookup, manual journal entries, and disconnected reporting workflows.

---

## The ERP Compliance Gap

| Platform | Native FASB ASU 2023-08 Automation | Typical Gap |
|---|---:|---|
| SAP S/4HANA | Limited / custom | Often requires specialized development |
| Oracle NetSuite | Limited / custom | Often requires SuiteScript customization |
| Microsoft Dynamics 365 | Limited / custom | No standard digital asset accounting workflow |
| Odoo Community | Not available by default | No official open-source compliance module |
| This Framework | Yes — open-source | Built for Odoo-based SME workflows |

This framework provides an affordable, open-source path for Odoo-based businesses and implementation partners to begin automating digital asset accounting workflows.

---

## The Solution

This repository provides a three-component Odoo-based framework:

### 1. ERP-Payment Integration Layer

A modular integration layer for importing digital asset transaction records from external payment providers.

Planned / supported connector patterns include:

- Coinbase Commerce
- BitPay
- BTCPay Server
- CoinGate
- webhook-based payment processors
- extensible provider adapters

The integration layer is designed for **read-only transaction ingestion** and does not initiate, route, or custody funds.

### 2. Automated Compliance Engine

A compliance automation layer for:

- fair-value capture at transaction time
- period-end fair-value remeasurement
- automated gain/loss calculation
- automated journal entry generation
- audit trail preservation
- disclosure schedule support
- tax lot and cost-basis tracking

### 3. Reporting & Disclosure Layer

Reporting tools for:

- FASB ASU 2023-08 disclosure schedules
- crypto asset movement reports
- fair-value remeasurement summaries
- audit-ready transaction traceability
- IRS Form 8949-ready cost basis output

---

## Production Background

This framework is not a purely theoretical research project.

It is based on ERP architecture patterns already used in production deployments involving:

- payment gateway integrations
- API polling and webhook processing
- automated accounting entries
- multi-currency reconciliation
- audit-ready financial workflows
- Odoo-based financial automation

The open-source release formalizes these patterns into a reusable framework for Odoo-based digital asset accounting compliance.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                         ODOO ERP                            │
│                                                             │
│  ┌──────────────┐   ┌────────────────┐   ┌───────────────┐ │
│  │ Accounting   │   │ FASB Engine    │   │ Reporting     │ │
│  │ Journal      │◄──│ Fair Value     │──►│ Disclosure    │ │
│  └──────┬───────┘   │ Gain/Loss      │   └───────────────┘ │
│         │           └───────┬────────┘                     │
│         │                   │                              │
│  ┌──────▼───────────────────▼───────────────────────────┐  │
│  │             Payment Integration Layer                 │  │
│  │  Webhooks | API Polling | Transaction Normalization   │  │
│  └───────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │ Coinbase    │  │ BitPay      │  │ BTCPay /    │
   │ Commerce    │  │            │  │ CoinGate    │
   └─────────────┘  └─────────────┘  └─────────────┘
