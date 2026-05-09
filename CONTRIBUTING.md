# Contributing

Thank you for your interest in this ERP-native digital-asset accounting and compliance infrastructure framework.

This repository welcomes professional feedback from Odoo developers, ERP consultants, CPAs, accounting professionals, tax preparers, fintech integrators, and security reviewers.

## Contribution Priorities

- Improve Odoo module quality while preserving working behavior.
- Improve documentation clarity and traceability.
- Add fake demonstration data and test fixtures.
- Add standards-mapping support for professional review.
- Identify security, privacy, accounting, tax, or audit-review risks.
- Clarify which features are implemented and which are planned.

## Contribution Rules

- Do not commit real client data, API keys, private keys, wallet seed phrases, webhook secrets, or production logs.
- Do not describe outputs as final tax filings, legal advice, audit opinions, or CPA replacements.
- Do not claim government approval, direct IRS integration, guaranteed compliance, guaranteed adoption, or production readiness unless supported by repository evidence.
- Use conservative wording such as "reference implementation," "sample workflow," "readiness output," "reviewable support schedule," and "professional review."
- Keep accounting and tax outputs framed as support materials for qualified professionals.

## Development Notes

- Follow Odoo conventions for manifests, views, models, security access files, and assets.
- Keep changes scoped and documented.
- Add or update sample files only with fake data.
- Run available checks before submitting a pull request.

Suggested local checks:

```bash
python3 -m compileall crypto_payment_sync
python3 - <<'PY'
from pathlib import Path
from xml.etree import ElementTree as ET
for path in Path("crypto_payment_sync").rglob("*.xml"):
    ET.parse(path)
print("XML parse check passed")
PY
```

## Professional Feedback

Professional feedback may address whether the documentation and sample outputs are understandable, reviewable, and appropriately limited. This project does not ask contributors to provide legal, tax, audit, or accounting advice through GitHub.
