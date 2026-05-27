# AGENTS.md

## Repository Purpose

This repository is a public reference implementation and documentation package for an ERP-native digital-asset accounting and compliance infrastructure framework. It is designed to show how digital-asset transaction data can be mapped into Odoo/ERP accounting workflows, CPA-reviewable audit evidence, and structured tax-reporting readiness outputs.

Keep all wording conservative, evidence-based, and aligned with the repository's actual contents.

## Do-Not-Overclaim Rules

Do not state or imply that this project is government-approved, IRS-approved, SEC-approved, or endorsed by any agency.

Do not state or imply direct IRS integration, automated filing, final return preparation, or guaranteed compliance.

Do not state or imply that this project replaces CPAs, auditors, tax preparers, attorneys, or professional judgment.

Do not claim nationwide deployment, production readiness, guaranteed adoption, or real-client validation unless the repository contains clear evidence supporting that claim.

Use conservative wording such as:

- reference implementation
- standards-mapping framework
- designed to support professional review
- tax-reporting readiness outputs
- CPA-reviewable evidence package
- sample workflow
- demonstration data
- planned module
- prototype
- implementation pathway

All accounting and tax outputs must be described as reviewable support materials, not final filings, legal advice, tax advice, audit opinions, or compliance certifications.

## Coding Conventions

- Preserve working Odoo functionality unless a change is clearly required.
- Keep changes narrowly scoped and consistent with the existing module structure.
- Prefer explicit model, field, and method names that match Odoo conventions.
- Avoid committing credentials, API keys, private keys, wallet seed phrases, real client data, webhook secrets, or production logs.
- Use fake/sample data for examples.
- Add comments only when they clarify non-obvious accounting, tax, security, or Odoo behavior.
- Do not add broad dependencies without documenting why they are needed.

## Odoo Module Conventions

- Keep Odoo addon code under `crypto_payment_sync/` unless a new planned module is intentionally scaffolded.
- Update `__manifest__.py` when adding Odoo data files, views, assets, or dependencies.
- Keep XML view IDs stable and namespaced to the module.
- Keep access controls in `security/ir.model.access.csv` aligned with new models.
- Treat external API calls as optional integration points that require sandbox credentials and reviewer validation.
- Do not imply custody, exchange, money transmission, or regulated financial-intermediary status from the reference implementation.

## Documentation Conventions

- Use clear, professional Markdown.
- Separate implemented features from planned modules and implementation pathways.
- Mark sample data and sample outputs as fake demonstration materials.
- Use terms like "readiness," "mapping support," "reviewable schedule," and "professional review" for tax and accounting outputs.
- Include disclaimers where documentation discusses tax, accounting, audit, legal, regulatory, or securities topics.

## Testing and Verification

Run available non-destructive checks before finalizing changes. Useful checks include:

```bash
python3 -m compileall crypto_payment_sync
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
for path in Path("crypto_payment_sync").rglob("*.xml"):
    ET.parse(path)
print("XML parse check passed")
PY
git status --short
```

If a full Odoo test environment is unavailable, say so clearly. Do not invent test results.

## Professional Review Boundary

Accounting, tax, audit, legal, and regulatory conclusions must remain outside the repository's claims. The repository may provide technical support schedules, field mappings, reconciliation status, and evidence packaging designed for professional review. It must not present those materials as final filings or professional advice.
