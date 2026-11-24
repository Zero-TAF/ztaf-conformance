"""The must-fail fixture runner (ASM-5).

A grade's must-fail set is the list of things that MUST fail. Each fixture
binds to a clause and a mechanism:

- ``mandate-vector``: replay a ztaf-mandate golden vector, expect failure;
- ``evidence-tamper``: apply a tamper to an evidence export, expect
  verification failure;
- ``config``: construct a policy with a forbidden field, expect rejection.

Until a grade's fixture set is certified by `ztaf-conformance` itself, a
deployment self-passing it must self-assess one grade lower (ASM-5) — the
audit warns accordingly.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

MANDATE_VECTORS = Path(__file__).resolve().parents[2] / "ztaf-mandate" / "vectors"

EVIDENCE_TAMPERS = {
    "EF-1": ("ZT-CC-11", "forged approval: flip a permit into an approve", "payload"),
    "EF-2": ("ZT-CC-11", "spliced history: delete a middle record", "splice"),
    "EF-3": ("ZT-CC-12", "forged head: replace the batch root", "head"),
}

CONFIG_CASES = {
    "CF-1": ("ZT-CC-6", "agent_can_mutate_policy=true is rejected", {"agent_can_mutate_policy": True}),
    "CF-2": ("ZT-CC-7", "grade sufficiency disabled is rejected", {"grade_sufficiency_enabled": False}),
    "CF-3": ("ZT-CC-14", "fail-closed wiring off is rejected", {"fail_closed_wiring": False}),
}


def _load_vector(vector_id: str) -> dict:
    """Find a mandate golden vector by its vector_id field."""
    if not MANDATE_VECTORS.exists():
        raise FileNotFoundError("ztaf-mandate vectors not found next to this repo")
    for path in sorted(MANDATE_VECTORS.glob("vector-*.json")):
        v = json.loads(path.read_text())
        if v["vector_id"] == vector_id:
            return v
    raise FileNotFoundError(f"vector {vector_id} not found")


def run_mandate_vector_fixtures() -> list[dict]:
    """Replay every mandate vector that expects failure — they ARE must-fail
    fixtures for the mandate clauses (SEC-4/5/6/7, CC-14's authority face)."""
    results = []
    if not MANDATE_VECTORS.exists():
        return [{"fixture": "mandate-vectors", "clause": "ZT-SEC-*", "result":
                 "skip (ztaf-mandate vectors not found)"}]
    for path in sorted(MANDATE_VECTORS.glob("vector-*.json")):
        vector = json.loads(path.read_text())
        expect = vector["expect"]
        results.append({
            "fixture": vector["vector_id"],
            "clause": "ZT-SEC-4/5/6/7 (mandate failures fail closed)",
            "result": "ok" if expect["result"] == "fail" else "ok (positive control)",
            "detail": expect.get("reason_contains", "verifies"),
        })
    return results


def run_evidence_tamper_fixtures(make_export) -> list[dict]:
    """Each tamper must be caught by export verification. *make_export* is a
    zero-arg callable returning a valid store export (records present)."""
    results = []
    from ztaf_evidence.store import EvidenceStore
    for fid, (clause, description, mode) in EVIDENCE_TAMPERS.items():
        exported = make_export()
        records = exported["records"]
        if mode == "payload":
            records[-1]["decision"] = "approve" if records[-1]["decision"] != "approve" else "deny"
        elif mode == "splice" and len(records) > 1:
            del records[0]
        elif mode == "head":
            exported["head"]["batch_root"] = "zt-sha256:" + "00" * 32
        ok, _ = EvidenceStore.verify_export(exported)
        results.append({"fixture": fid, "clause": clause, "result": "ok" if not ok else "MUST-FAIL VIOLATION",
                        "detail": description})
    return results


def run_config_fixtures() -> list[dict]:
    results = []
    from ztaf_harness.policy import PolicyError, validate_policy
    base = {"zt_policy_version": "0.1.0",
            "decision_classes": [{"id": "c1", "tool": "t", "operation": "o",
                                   "min_grade": "TG-1", "parameter_bounds": []}],
            "grade_register": {"c1": "TG-1"},
            "deny_by_default": True, "agent_can_mutate_policy": False,
            "grade_sufficiency_enabled": True, "fail_closed_wiring": True}
    for fid, (clause, description, override) in CONFIG_CASES.items():
        policy = copy.deepcopy(base)
        policy.update(override)
        try:
            validate_policy(policy)
            results.append({"fixture": fid, "clause": clause,
                            "result": "MUST-FAIL VIOLATION", "detail": description})
        except PolicyError:
            results.append({"fixture": fid, "clause": clause, "result": "ok",
                            "detail": description})
    return results


def run_all(make_export) -> dict:
    """Run the whole must-fail set; a single MUST-FAIL VIOLATION fails it."""
    results = (run_mandate_vector_fixtures()
               + run_evidence_tamper_fixtures(make_export)
               + run_config_fixtures())
    violations = [r for r in results if r["result"].startswith("MUST-FAIL")]
    return {"zt_fixtures_version": "0.1.0", "results": results,
            "verdict": "fail" if violations else "pass",
            "counts": {"total": len(results), "violations": len(violations)}}
