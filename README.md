# ztaf-conformance

The must-fail fixture runner and **ztaf-audit**: a deployment bundle in, a grade card out.

| Field | Value |
|---|---|
| Authority | Reference — normative conformance clauses (ZT-CC): [ztaf-spec](https://github.com/Zero-TAF/ztaf-spec); grade scheme: ADR-ZTAF-0005 |
| Tier | T5 (assurance) |
| Wave | W5 |
| Version | 0.1.0 |
| Status | Active |
| Licence | MIT |

## What this repository owns

- `ztaf_conformance/audit.py` — the audit engine: nine checks over a deployment bundle (policy + claims + fixtures + evidence export), each bound to a ZT-CC clause; grade cards per decision class; **grade honesty is the spine** — claimed above evidenced is a failure, not a reporting choice (ASM-3).
- `ztaf_conformance/fixtures.py` — the must-fail set (ASM-5): the ztaf-mandate golden vectors (mandate failures fail closed), three evidence-tamper cases (forged payload, spliced history, forged head), three config rejections (agent-mutable policy, sufficiency disabled, fail-closed off). A single MUST-FAIL VIOLATION fails the set.
- `ztaf_conformance/cli.py` — `ztaf-audit audit --bundle b.json` and `ztaf-audit fixtures`.
- `tests/` — 8 tests, including the FIND-0001 lesson encoded: a blind verifier that always says "ok" MUST make the fixture set fail.

## What this repository does not own

- Normative clauses — [ztaf-spec](https://github.com/Zero-TAF/ztaf-spec); the runtime being audited — [ztaf-reference-harness](https://github.com/Zero-TAF/ztaf-reference-harness); behavioural metrics — [ztaf-evaluation](https://github.com/Zero-TAF/ztaf-evaluation).
- Certification itself: no scheme here certifies anyone; TG-4's third-party attestation is a human process (see `docs/certification-process.md`).

## Running

```bash
python -m ztaf_conformance.cli fixtures                       # the must-fail set
python -m ztaf_conformance.cli audit --bundle bundle.json     # a grade card
```

Bundle shape: see `tests/test_conformance.py::good_bundle` — it is exactly what `ztaf-harness demo` produces plus the claims and fixtures fields.
