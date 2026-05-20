# Release Snapshot Note

## Recommended manual release/tag name

`v0.1-rfe-documentation-snapshot`

## Purpose

Use this optional release or tag to create a stable public snapshot for a short Exhibit P1-K repository documentation package. The snapshot should help reviewers cite the same repository state shown in screenshots.

## Before creating the release/tag

- Confirm the README links work.
- Confirm `docs/`, `sample_data/`, `sample_outputs/`, `tests/`, and `exhibit_assets/` are visible on GitHub.
- Run available non-destructive checks, such as Python compilation, XML parsing, and unit tests.
- Confirm sample data and sample outputs are fake demonstration materials only.
- Confirm no credentials, API keys, private keys, wallet seed phrases, webhook secrets, production logs, or real client data are present.
- Confirm documentation continues to avoid claims of government endorsement, IRS integration, automatic filing, certification, guaranteed compliance, or guaranteed adoption.

## Snapshot boundary

This release/tag should be described as a documentation and reference-implementation snapshot. It is not a production certification, compliance certification, audit opinion, tax opinion, legal opinion, or government endorsement.

