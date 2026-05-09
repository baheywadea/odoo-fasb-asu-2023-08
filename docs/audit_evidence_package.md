# Audit Evidence Package

This document describes the intended structure of a CPA-reviewable audit evidence package for digital-asset accounting workflows.

## Purpose

The package is designed to help reviewers trace accounting outputs back to source records, valuation support, reconciliation status, and preparer notes. It is not an audit opinion and does not replace audit procedures.

## Suggested Evidence Components

- Source transaction export or API reference.
- Normalized ledger record.
- Wallet, provider, network, and address metadata when relevant.
- Fair-value support record with price source and source timestamp.
- Draft journal-entry preparation record.
- Reconciliation status and exception notes.
- Reviewer sign-off fields or review workflow status.
- Version information for the module or script used to generate the support file.

## Evidence Quality Principles

- Preserve source identifiers.
- Keep fake/sample data separate from client data.
- Record valuation source and timestamp.
- Avoid overwriting source data during normalization.
- Track exceptions instead of hiding them.
- Keep outputs reviewable by CPAs, auditors, or tax professionals.

## Current Repository Status

The repository includes a sample evidence summary at `sample_outputs/audit_evidence_package_summary.md`. It is fake demonstration material and should be used only to show the intended review structure.
