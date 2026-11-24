"""Conformance audit + fixture runner tests (run from repo root)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sibling in ("ztaf-mandate", "ztaf-evidence", "ztaf-reference-harness"):
    p = ROOT.parent / sibling
    if p.exists():
        sys.path.insert(0, str(p))
sys.path.insert(0, str(ROOT))

from ztaf_conformance.audit import audit, render  # noqa: E402
from ztaf_conformance.fixtures import run_all  # noqa: E402
from ztaf_evidence.store import EvidenceStore  # noqa: E402


def good_policy():
    return {
        "zt_policy_version": "0.1.0",
        "decision_classes": [{
            "id": "refund-agent-42.payments-api.refund", "tool": "payments-api",
            "operation": "refund", "min_grade": "TG-2",
            "parameter_bounds": [{"field": "amount", "op": "max", "bound": 500}],
            "escalation": {"field": "amount", "op": "max", "bound": 200},
        }],
        "grade_register": {"refund-agent-42.payments-api.refund": "TG-2"},
        "deny_by_default": True, "agent_can_mutate_policy": False,
        "grade_sufficiency_enabled": True, "fail_closed_wiring": True,
    }


def make_export():
    store = EvidenceStore()
    for i, decision in enumerate(("permit", "escalate", "deny"), 1):
        rec = {"zt_record_version": "0.1.0", "record_id": f"rec-{i}",
               "timestamp": "2026-11-24T00:00:00Z", "task_identity": f"task-{i}",
               "mandate_id": "ZT-MND-A", "mandate_hash": "zt-sha256:" + "ab" * 32,
               "decision_class": "refund-agent-42.payments-api.refund",
               "action": {"tool": "payments-api", "operation": "refund",
                          "parameters_hash": "zt-sha256:" + "cd" * 32},
               "rule_applied": "POL-1", "decision": decision,
               "required_grade": "TG-2", "evidenced_grade": "TG-2"}
        if decision == "escalate":
            rec["evidence_bundle_hash"] = "zt-sha256:" + "bd" * 32
        store.append(rec)
    return store.export()


def good_bundle(**over):
    bundle = {
        "zt_bundle_version": "0.1.0",
        "deployment": {"name": "refund-desk-demo", "topology": "T1-harness-embedded"},
        "policy": good_policy(),
        "claims": {"refund-agent-42.payments-api.refund": "TG-2"},
        "fixtures_passed": {"TG-2": True},
        "fixture_provenance": "certified",
        "evidence_export": make_export(),
    }
    bundle.update(over)
    return bundle


class TestAudit(unittest.TestCase):
    def test_compliant_bundle_passes_at_tg2(self):
        report = audit(good_bundle())
        self.assertEqual(report["verdict"], "pass", json.dumps(report["failures"], indent=2))
        self.assertEqual(report["grade_cards"][0]["verdict"], "pass")

    def test_grade_inflation_fails_cc13(self):
        report = audit(good_bundle(claims={"refund-agent-42.payments-api.refund": "TG-3"}))
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(any(f["clause"] == "ZT-CC-13" for f in report["failures"]))

    def test_tg3_claim_without_receipts_fails_cc12(self):
        report = audit(good_bundle(
            claims={"refund-agent-42.payments-api.refund": "TG-3"},
            policy={**good_policy(), "grade_register":
                    {"refund-agent-42.payments-api.refund": "TG-3"}}))
        self.assertTrue(any(f["clause"] == "ZT-CC-12" for f in report["failures"]))

    def test_unpassed_fixtures_fail_cc13(self):
        report = audit(good_bundle(fixtures_passed={"TG-2": False}))
        self.assertEqual(report["verdict"], "fail")
        self.assertTrue(any(f["clause"] == "ZT-CC-13" for f in report["failures"]))

    def test_tampered_evidence_fails_cc11(self):
        bundle = good_bundle()
        bundle["evidence_export"]["records"][0]["decision"] = "approve"
        report = audit(bundle)
        self.assertTrue(any(f["clause"] == "ZT-CC-11" for f in report["failures"]))

    def test_render_is_human_readable(self):
        text = render(audit(good_bundle()))
        self.assertIn("verdict: PASS", text)
        self.assertIn("Claims beyond evidence", text)


class TestMustFailFixtures(unittest.TestCase):
    def test_full_set_passes_and_detects(self):
        report = run_all(make_export)
        self.assertEqual(report["verdict"], "pass", json.dumps(report, indent=2))
        self.assertGreaterEqual(report["counts"]["total"], 14)

    def test_must_fail_actually_fails_when_broken(self):
        # Sanity: if the tamper runner were handed a verifier that always
        # says ok, the fixtures MUST fail — this is the FIND-0001 lesson in
        # miniature.
        from ztaf_evidence.store import EvidenceStore as ES

        class BlindStore(ES):
            @staticmethod
            def verify_export(exported):  # noqa: N802
                return True, None

        original = ES.verify_export
        ES.verify_export = BlindStore.verify_export
        try:
            report = run_all(make_export)
            self.assertEqual(report["verdict"], "fail")
            self.assertGreater(report["counts"]["violations"], 0)
        finally:
            ES.verify_export = original


if __name__ == "__main__":
    unittest.main()
