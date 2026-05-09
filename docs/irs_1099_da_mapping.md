# IRS Form 1099-DA Mapping Readiness

This document describes field-mapping readiness for IRS Form 1099-DA support. It does not provide tax advice, does not file information returns, and does not connect directly to IRS systems.

## Purpose

The goal is to preserve and normalize transaction data that may help tax professionals prepare or review digital-asset information-reporting workflows. The mapping is a readiness layer, not a filing engine.

## Candidate Mapping Fields

| Readiness Field | Source Example | Review Notes |
|---|---|---|
| Transaction ID | Provider reference, blockchain hash, exchange export ID | Preserves source traceability. |
| Asset disposed or transferred | Asset symbol/name | Requires professional classification. |
| Quantity | Source transaction amount | Requires unit precision review. |
| Transaction date/time | Source timestamp | Time zone and reporting date rules require review. |
| Gross proceeds support | ERP or provider amount | Requires entity-specific tax review. |
| Cost-basis support reference | Internal lot or ERP support schedule | May require separate tax-lot methodology review. |
| Counterparty or address metadata | Wallet/payment records when available | May be incomplete or not reportable depending on context. |
| Reconciliation status | Matched, unmatched, exception | Supports reviewer workflow. |

## Implementation Notes

The current repository contains Odoo records that can preserve provider, wallet, network, and transaction references. Future implementation phases may add structured 1099-DA readiness exports for professional review.

## Important Limitations

This project does not decide reporting obligations, broker status, payee classification, withholding, filing deadlines, or final form content. Qualified tax professionals must review all reporting decisions.
