"""The ztaf-audit engine: a deployment bundle in, a grade card out.

The bundle is the utilitarian contract of Wave 5: policy, claims, fixtures,
and an evidence export — exactly what the Wave 4 demo writes. The audit
checks the automatable subset of the conformance clauses (ZT-CC, ztaf-spec)
and grade honesty (ASM-3): claims above evidence are conformance failures.
"""

from __future__ import annotations

from typing import Any, Optional

from ztaf_evidence.store import EvidenceStore
from ztaf_mandate.constraints import grade_rank

BUNDLE_VERSION = "0.1.0"

# checks: (audit_id, clause, description)
CHECKS = [
    ("A1", "ZT-CC-1", "decision classes declared"),
    ("A2", "ZT-CC-4", "class specificity: tool, operation, min_grade, bounds or escalation"),
    ("A3", "ZT-CC-6", "configuration honesty: agent cannot mutate policy"),
    ("A4", "ZT-CC-7", "grade-sufficiency check enabled"),
    ("A5", "ZT-CC-9", "deny-by-default egress/capability posture declared"),
    ("A6", "ZT-CC-11", "evidence chain verifies (append-only, hash-linked)"),
    ("A7", "ZT-CC-12", "independent verification: export head reproduces; receipts at TG-3+"),
    ("A8", "ZT-CC-13", "grade honesty: claimed <= evidenced; grade fixtures passed"),
    ("A9", "ZT-CC-14", "fail-closed wiring declared"),
]


def audit(bundle: dict) -> dict:
    if bundle.get("zt_bundle_version") != BUNDLE_VERSION:
        raise ValueError(f"bundle version must be {BUNDLE_VERSION}")
    policy = bundle["policy"]
    claims: dict[str, str] = bundle.get("claims", {})
    fixtures: dict[str, bool] = bundle.get("fixtures_passed", {})
    export = bundle.get("evidence_export")

    failures: list[dict] = []
    warnings: list[str] = []
    cards: list[dict] = []

    # A1 CC-1
    classes = {c["id"]: c for c in policy.get("decision_classes", [])}
    if not classes:
        failures.append({"audit": "A1", "clause": "ZT-CC-1", "detail": "no decision classes declared"})

    # A2 CC-4
    for cid, c in classes.items():
        specific = all(c.get(k) for k in ("tool", "operation")) and c.get("min_grade") \
            and (c.get("parameter_bounds") or c.get("escalation"))
        if not specific:
            failures.append({"audit": "A2", "clause": "ZT-CC-4", "detail": f"class {cid} not specific"})

    # A3 CC-6 / A4 CC-7 / A9 CC-14
    if policy.get("agent_can_mutate_policy", False):
        failures.append({"audit": "A3", "clause": "ZT-CC-6", "detail": "agent_can_mutate_policy is true"})
    if not policy.get("grade_sufficiency_enabled", False):
        failures.append({"audit": "A4", "clause": "ZT-CC-7", "detail": "grade sufficiency disabled"})
    if not (policy.get("fail_closed_wiring") and policy.get("deny_by_default")):
        failures.append({"audit": "A9", "clause": "ZT-CC-14", "detail": "fail-closed wiring incomplete"})

    # A5 CC-9
    if not policy.get("deny_by_default"):
        failures.append({"audit": "A5", "clause": "ZT-CC-9", "detail": "not deny-by-default"})

    # A6/A7 CC-11/CC-12
    head_ok = False
    receipts_seen = 0
    if export:
        head_ok, reason = EvidenceStore.verify_export(export)
        if not head_ok:
            failures.append({"audit": "A6", "clause": "ZT-CC-11",
                             "detail": f"evidence chain fails: {reason}"})
        records = export.get("records", [])
        receipts_seen = sum(1 for r in records if r.get("transparency"))
        top_claim = max((grade_rank(g) for g in claims.values()), default=0)
        if top_claim >= grade_rank("TG-3") and receipts_seen == 0:
            failures.append({"audit": "A7", "clause": "ZT-CC-12",
                             "detail": "TG-3+ claimed but no transparency receipts in records"})
    else:
        warnings.append("no evidence export in bundle: A6/A7 not checkable (report as unproven)")

    # A8 CC-13 grade honesty, per class
    register = policy.get("grade_register", {})
    for cid, claimed in claims.items():
        evidenced = register.get(cid)
        class_fail = []
        if evidenced is None:
            class_fail.append("no evidenced grade in register")
        elif grade_rank(claimed) > grade_rank(evidenced):
            class_fail.append(f"claimed {claimed} > evidenced {evidenced}")
        needed = grade_rank(claimed)
        for grade, passed in fixtures.items():
            if grade_rank(grade) <= needed and not passed:
                class_fail.append(f"grade-{grade} must-fail fixtures not passed")
        if class_fail:
            failures.append({"audit": "A8", "clause": "ZT-CC-13",
                             "detail": f"class {cid}: " + "; ".join(class_fail)})
        cards.append({"decision_class": cid, "claimed": claimed,
                      "evidenced": evidenced, "verdict": "pass" if not class_fail else "fail",
                      "failing": class_fail})

    if fixtures.get("TG-2") and "certified" not in bundle.get("fixture_provenance", "certified"):
        warnings.append("fixture provenance: programmes self-passing fixtures below TG-3 should "
                        "self-assess one grade lower until ztaf-conformance certifies the set (ASM-5)")

    verdict = "pass" if not failures else "fail"
    return {
        "zt_audit_version": "0.1.0",
        "deployment": bundle.get("deployment", {}),
        "verdict": verdict,
        "grade_cards": cards,
        "failures": failures,
        "warnings": warnings,
        "checks_run": [{"audit": a, "clause": c, "check": d,
                        "result": _result(a, failures)} for a, c, d in CHECKS],
        "evidence": {"records": len(export.get("records", [])) if export else 0,
                     "head_verified": head_ok, "receipts": receipts_seen},
        "claim": "Claims beyond evidence are conformance failures, not reporting choices (ASM-3).",
    }


def _result(audit_id: str, failures: list[dict]) -> str:
    hits = [f for f in failures if f["audit"] == audit_id]
    return "fail" if hits else ("pass" if hits is not None else "n/a")


def render(report: dict) -> str:
    lines = []
    dep = report.get("deployment", {})
    lines.append(f"ztaf-audit — {dep.get('name', 'deployment')} "
                 f"({dep.get('topology', 'topology undeclared')})")
    lines.append(f"verdict: {report['verdict'].upper()}")
    for card in report["grade_cards"]:
        lines.append(f"  {card['decision_class']}: claimed {card['claimed']} / "
                     f"evidenced {card['evidenced']} -> {card['verdict']}"
                     + (f"  [{'; '.join(card['failing'])}]" if card["failing"] else ""))
    for f in report["failures"]:
        lines.append(f"  FAIL {f['audit']} {f['clause']}: {f['detail']}")
    for w in report["warnings"]:
        lines.append(f"  note {w}")
    ev = report["evidence"]
    lines.append(f"evidence: {ev['records']} records, head {'verified' if ev['head_verified'] else 'NOT verified'}, "
                 f"{ev['receipts']} anchored")
    lines.append(report["claim"])
    return "\n".join(lines)
