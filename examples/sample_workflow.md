# Sample Workflow

This example uses fake demonstration data only.

## Steps

1. Import source transactions from `sample_data/digital_asset_transactions.csv`.
2. Normalize source fields into asset, quantity, timestamp, wallet/account, network, and source-reference fields.
3. Prepare fair-value support records using `sample_outputs/fair_value_records_sample.csv` as the expected output shape.
4. Prepare draft journal-entry support rows using `sample_outputs/journal_entries_sample.csv`.
5. Identify disposition events and prepare reconciliation support using `sample_outputs/form_8949_reconciliation_sample.csv`.
6. Package support schedules and reviewer notes using `sample_outputs/audit_evidence_package_summary.md`.
7. Submit the package for qualified professional review before any accounting, audit, tax, or reporting use.

## Boundary

The workflow demonstrates data organization and traceability. It does not file returns, submit information returns, connect to IRS systems, certify fair value, or replace CPAs, auditors, tax preparers, attorneys, or professional judgment.
