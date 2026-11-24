# The Certification Process (Outline)

**Version 0.1.0. Outline, not a scheme.** This document states what a certification process for Tough Grades must contain when the programme stands one up (a change request, owner-gated). It certifies nothing today.

## Stages

1. **Fixture certification.** The must-fail set per grade (this repository's runner) is reviewed and version-pinned; a fixture release is signed and its provenance recorded. Until then, every self-passed fixture forces one-grade-down self-assessment (ASM-5).
2. **Auditor independence.** TG-4 requires third-party attestation (ASM-8): the auditor is not the operator, not the tool vendor, and not the programme owner. Independence rules follow the estate's reviewer-independence pattern.
3. **Evidence review.** The auditor walks the store export: chain, head, receipts (TG-3+), escalation bundles, approval attributions — the artifacts `ztaf-audit` already checks, plus sampled human ruling quality (OVR-6).
4. **Attestation.** A signed statement over the audited bundle hash and grade cards, themselves anchorable via the evidence plane's transparency profile.
5. **Currency.** A certification has a validity window and falls with incidents (ASM-6): re-proof, not renewal paperwork.

## Non-goals

No legal conformity claim (ASM-7); no model scoring; no vendor accreditation marketplace. The grades grade the evidence regime of delegated decisions — that is all they have ever claimed.
