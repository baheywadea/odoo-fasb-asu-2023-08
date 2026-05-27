# FASB ASU 2023-08 Mapping

This document outlines a conservative mapping framework for supporting FASB ASU 2023-08 fair-value accounting workflows in an ERP environment. It is technical documentation only and is not accounting advice.

## Purpose

FASB ASU 2023-08 requires qualifying crypto assets within its scope to be measured at fair value, with changes in fair value recognized in net income. This repository documents a reference pathway for capturing the data needed to support professional review of those accounting records.

## Supported Data Concepts

| Concept | Example Field | Review Purpose |
|---|---|---|
| Asset identifier | `asset_symbol`, `asset_name` | Identify the digital asset being measured. |
| Quantity held | `quantity` | Support fair-value calculation and reconciliation. |
| Measurement date | `measurement_date` | Tie fair value to a reporting or transaction date. |
| Fair-value price | `fair_value_usd` | Support measurement of carrying value. |
| Price source | `price_source` | Document source used for professional review. |
| Source timestamp | `source_timestamp` | Support audit trail and repeatability. |
| Cost basis support | `cost_basis_usd` | Support unrealized gain/loss review. |
| Unrealized gain/loss | `unrealized_gain_loss_usd` | Support draft accounting entries. |

## ERP Mapping

The intended ERP mapping is:

1. Import or synchronize transaction records.
2. Normalize asset, quantity, timestamp, wallet, provider, and source reference data.
3. Capture fair-value support records at transaction date and reporting date.
4. Prepare draft journal-entry support rows for professional review.
5. Package supporting records for CPA or auditor review.

## Review Boundary

This framework does not determine whether a specific asset or entity is within the scope of ASU 2023-08. It does not certify fair value, accounting policy, disclosure adequacy, or financial statement presentation. Those decisions require qualified professional review.
