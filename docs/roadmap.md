# Roadmap

This roadmap describes a conservative implementation pathway. It does not claim that planned modules are complete unless they exist in the repository.

## Phase 1: Documentation and Reference Implementation

- Maintain the `crypto_payment_sync` Odoo module as a reference implementation for transaction and payment synchronization patterns.
- Add public documentation for architecture, review scope, standards mapping, and disclaimers.
- Provide fake sample data and fake sample outputs.
- Keep repository claims aligned with inspectable files.
- Add current-state and implementation-plan documentation.
- Add read-only adapter and normalizer helpers with fake fixtures.

## Phase 2: Accounting Core and Fair-Value Mapping

- Maintain and extend structured fair-value support records.
- Add source-price traceability fields and verified live exchange-rate adapter usage.
- Add cost-basis support models or import formats.
- Maintain and extend draft journal-entry support rows for professional review.
- Document accounting policy assumptions separately from code.

## Phase 3: Audit Evidence and Tax-Reporting Readiness

- Extend CPA-reviewable evidence package exports.
- Extend exception and reconciliation status workflows.
- Extend IRS Form 1099-DA field-mapping readiness outputs.
- Extend Form 8949 reconciliation support schedules.
- Add reviewer notes and sign-off metadata.

## Phase 4: Portability and Practitioner Feedback

- Improve portability across Odoo deployments and accounting configurations.
- Gather structured feedback from ERP implementers, CPAs, tax preparers, and technical reviewers.
- Add test fixtures and implementation examples based on non-sensitive demonstration data.
- Improve security hardening guidance for external API integrations.
