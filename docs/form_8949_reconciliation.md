# Form 8949 Reconciliation Support

This document describes a technical support workflow for reconciling digital-asset disposition records to Form 8949-style review schedules. It is not tax advice and does not create final tax filings.

## Purpose

The framework is intended to help organize source transactions, cost-basis support, proceeds support, and reconciliation status so tax professionals can review realized gain or loss calculations.

## Reconciliation Concepts

| Concept | Description |
|---|---|
| Disposition event | A sale, exchange, payment, transfer, or other event flagged for tax review. |
| Acquisition support | Source data used to support acquisition date, quantity, and cost basis. |
| Proceeds support | Source data used to support disposition value or proceeds. |
| Cost-basis method | FIFO, specific identification, or another method selected by the taxpayer and reviewer. |
| Adjustment notes | Reviewer notes for fees, rounding, transfers, missing basis, or classification. |
| Reconciliation status | Matched, exception, pending review, or excluded from sample output. |

## Example Output Shape

The sample file `sample_outputs/form_8949_reconciliation_sample.csv` demonstrates a review schedule shape using fake records. It is a support schedule only.

## Professional Review Boundary

The framework does not determine tax character, holding period, covered/noncovered status, wash-sale treatment, basis method validity, or final reportability. Those items require qualified tax review.
