# Screenshots to Capture for Exhibit P1-K

This checklist supports a short repository snapshot exhibit. The screenshots should show public inspectability, non-speculative implementation artifacts, and materials available for professional review. They should not be described as proving adoption, government endorsement, certification, or guaranteed compliance.

## Screenshot Checklist

| # | Screenshot title | Why it matters for Exhibit P1-K | What to highlight | Related USCIS/RFE concern it helps answer |
|---|---|---|---|---|
| 1 | GitHub repository homepage / branch overview | Supports public inspectability of the repository and branch. | Repository name, selected branch, visible files, recent commits. | Whether the project has public, reviewable artifacts rather than only a concept. |
| 2 | README project overview | Shows the repository's stated purpose and technical framing. | Odoo 19 reference module, documentation package, professional-review language. | Whether the work is concrete and understandable to outside reviewers. |
| 3 | README scope limitations | Shows conservative boundaries and avoids overclaiming. | "What the Project Does Not Do" and professional-review disclaimers. | Whether the record avoids unsupported claims of compliance, filing, or endorsement. |
| 4 | Repository structure | Shows implementation and documentation artifacts in one public location. | `crypto_payment_sync`, `docs`, `sample_data`, `sample_outputs`, `tests`. | Whether the repository contains inspectable implementation materials. |
| 5 | Docs folder | Shows organized technical documentation. | Architecture, mapping, review-scope, roadmap, and disclaimer files. | Whether technical reviewers can inspect supporting materials. |
| 6 | Architecture document | Shows the technical workflow and module boundaries. | Ingestion, normalized ledger, fair-value, journal-entry, audit-evidence, and tax-readiness layers. | Whether the implementation pathway is technically coherent. |
| 7 | FASB ASU 2023-08 mapping document | Shows standards-mapping support for fair-value workflows. | Supported data concepts and review boundary. | Whether the project addresses a specific accounting workflow without claiming accounting advice. |
| 8 | IRS Form 1099-DA mapping readiness document | Shows tax-reporting readiness mapping support. | Candidate fields, readiness framing, limitations. | Whether the project supports professional review without claiming IRS filing or integration. |
| 9 | Form 8949 reconciliation document | Shows reconciliation support for disposition review schedules. | Reconciliation concepts and sample output reference. | Whether the project includes practical tax-review support materials. |
| 10 | Audit evidence package document | Shows reviewer-facing evidence organization. | Evidence components, traceability principles, sample summary reference. | Whether CPAs or auditors can review source-to-output support. |
| 11 | Sample data folder | Shows fake input data for inspection and testing. | File names and any README/disclaimer identifying fake demonstration data. | Whether examples exist without using real client data. |
| 12 | Sample outputs folder | Shows fake output examples for reviewable support materials. | 1099-DA, Form 8949, journal entries, fair-value, reconciliation, and audit summary files. | Whether the repository includes concrete output artifacts. |
| 13 | 1099-DA readiness sample output | Shows an inspectable tax-readiness output shape. | Fake records, field names, readiness/review status. | Whether tax-readiness support is more than a narrative description. |
| 14 | Form 8949 reconciliation sample output | Shows a sample reconciliation support schedule. | Fake disposition rows, cost-basis/proceeds support, review status. | Whether Form 8949-related review support can be inspected. |
| 15 | Journal entry sample output | Shows ERP accounting preparation output. | Draft journal-entry support rows and review status. | Whether ERP-native accounting outputs are represented. |
| 16 | Audit evidence package summary | Shows reviewer-facing package structure. | Fake package metadata, included support files, reviewer notes. | Whether audit evidence can be organized for professional review. |
| 17 | Tests folder or test command output reference | Shows that non-destructive validation exists. | `tests/test_services.py` or terminal output for unit/static checks. | Whether the repository includes verification artifacts. |
| 18 | Commit history page | Shows development activity on the public branch. | Recent commits and branch context. | Whether there is visible implementation progress over time. |
| 19 | License page | Shows public reuse/review terms. | LGPL-3.0 license file. | Whether the repository is publicly inspectable under stated terms. |
| 20 | Security/professional review disclaimer page | Shows data-handling and review boundaries. | `SECURITY.md`, `docs/disclaimer.md`, or `docs/professional_review_scope.md`. | Whether the project avoids unsafe handling of secrets or unsupported professional claims. |
| 21 | Release/tag page, if available | Shows a stable snapshot for citation. | Recommended tag or release notes if manually created. | Whether the exhibit can cite a fixed repository snapshot. |

