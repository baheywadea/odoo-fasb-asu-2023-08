# Security Policy

## Scope

This repository includes an Odoo reference module and documentation for digital-asset transaction workflows. Security review is especially important because external API credentials, webhook callbacks, wallet records, and transaction data may be involved in real implementations.

## Do Not Commit

- API keys or provider credentials.
- Private keys, wallet seed phrases, mnemonic phrases, or signing secrets.
- Webhook secrets or callback tokens.
- Real client, taxpayer, customer, vendor, or employee data.
- Production logs containing transaction identifiers tied to real entities.
- Unredacted screenshots from production systems.

## Reporting Security Issues

Please report suspected security issues privately to the repository maintainer. Do not open a public issue containing secrets, exploit details, real transaction data, or personally identifiable information.

## Implementation Guidance

- Use sandbox credentials during development.
- Validate webhook authenticity before relying on callback data.
- Store credentials using Odoo-supported secret/configuration mechanisms.
- Restrict access to accounting, wallet, provider, and transaction records by role.
- Review outbound payment or transaction-signing workflows separately before any production use.

This policy is technical guidance only and is not legal, regulatory, audit, or security certification.
