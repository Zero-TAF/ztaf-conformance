"""The ztaf-audit CLI.

    python -m ztaf_conformance.cli audit --bundle bundle.json [--out report.json]
    python -m ztaf_conformance.cli fixtures [--out fixtures-report.json]

`audit` reads a deployment bundle (policy + claims + fixtures + evidence
export — what the Wave 4 demo writes) and prints the grade card.
`fixtures` runs the must-fail set and prints its verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit, render
from .fixtures import run_all


def cmd_audit(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text())
    report = audit(bundle)
    print(render(report))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
        print(f"report written to {args.out}")
    return 0 if report["verdict"] == "pass" else 1


def cmd_fixtures(args: argparse.Namespace) -> int:
    def make_export():
        # A tiny valid store: three honest records.
        from ztaf_evidence.store import EvidenceStore
        store = EvidenceStore()
        for i, decision in enumerate(("permit", "escalate", "deny"), 1):
            rec = {"zt_record_version": "0.1.0", "record_id": f"fx-{i}",
                   "timestamp": "2026-11-24T00:00:00Z",
                   "task_identity": f"task-{i}",
                   "mandate_id": "ZT-MND-FX", "mandate_hash": "zt-sha256:" + "ef" * 32,
                   "decision_class": "refund-issue",
                   "action": {"tool": "payments-api", "operation": "refund",
                              "parameters_hash": "zt-sha256:" + "f0" * 32},
                   "rule_applied": "POL-FX", "decision": decision,
                   "required_grade": "TG-2", "evidenced_grade": "TG-2"}
            if decision == "escalate":
                rec["evidence_bundle_hash"] = "zt-sha256:" + "bd" * 32
            store.append(rec)
        return store.export()

    report = run_all(make_export)
    for r in report["results"]:
        print(f"  {r['result']:>22}  {r['fixture']:<12} {r['clause']}")
    print(f"must-fail verdict: {report['verdict']} ({report['counts']['violations']} "
          f"violations across {report['counts']['total']} fixtures)")
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2))
    return 0 if report["verdict"] == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ztaf-audit")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--bundle", required=True)
    a.add_argument("--out", default=None)
    a.set_defaults(func=cmd_audit)
    f = sub.add_parser("fixtures")
    f.add_argument("--out", default=None)
    f.set_defaults(func=cmd_fixtures)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
