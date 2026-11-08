"""Unit tests for MasterBillingPolicyEngine + Guardrail integration."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from billing_governance import (  # noqa: E402
    BillingGovernanceGuardrail,
    MasterBillingPolicyEngine,
    MasterGovernanceExtension,
    OperationType,
    OperationalInput,
    PolicyRule,
    GovernancePolicyLevel,
)


class TestPolicyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MasterBillingPolicyEngine("owner-1")
        self.ext = MasterGovernanceExtension(self.engine)

    def test_empty_principal_raises(self):
        with self.assertRaises(ValueError):
            MasterBillingPolicyEngine("")

    def test_deny_wrong_principal(self):
        r = self.engine.evaluate({"principal_id": "x", "operation_type": "standard"})
        self.assertFalse(r.is_allowed)
        self.assertEqual(r.policy_id, "POL-001")

    def test_financial_requires_hitl(self):
        r = self.engine.evaluate(
            {
                "principal_id": "owner-1",
                "operation_type": "payment_method_update",
            }
        )
        self.assertTrue(r.is_allowed)
        self.assertTrue(r.requires_hitl)
        self.assertEqual(r.policy_id, "POL-002")

    def test_provisioning_auto(self):
        r = self.engine.evaluate(
            {
                "principal_id": "owner-1",
                "operation_type": "provisioning_execution",
            }
        )
        self.assertTrue(r.is_allowed)
        self.assertFalse(r.requires_hitl)
        self.assertEqual(r.policy_id, "POL-003")

    def test_standard_default(self):
        r = self.engine.evaluate(
            {"principal_id": "owner-1", "operation_type": "standard"}
        )
        self.assertTrue(r.is_allowed)
        self.assertFalse(r.requires_hitl)
        self.assertEqual(r.policy_id, "POL-DEFAULT")

    def test_intercept_blocked(self):
        out = self.ext.intercept_and_validate(
            {"principal_id": "intruder", "operation_type": "standard"}
        )
        self.assertEqual(out["status"], "blocked")

    def test_intercept_proceed_hitl(self):
        out = self.ext.intercept_and_validate(
            {
                "principal_id": "owner-1",
                "operation_type": "financial_transaction",
            }
        )
        self.assertEqual(out["status"], "proceed")
        self.assertTrue(out["requires_hitl"])

    def test_custom_rule(self):
        self.engine.add_rule(
            PolicyRule(
                rule_id="POL-X",
                description="Deny bulk refunds",
                target_operation="refund",
                policy_level=GovernancePolicyLevel.DENY_UNVERIFIED,
                condition=lambda ctx: ctx.get("payload", {}).get("action") == "bulk_refund",
            )
        )
        r = self.engine.evaluate(
            {
                "principal_id": "owner-1",
                "operation_type": "standard",
                "payload": {"action": "bulk_refund"},
            }
        )
        self.assertFalse(r.is_allowed)
        self.assertEqual(r.policy_id, "POL-X")


class TestGuardrailIntegration(unittest.TestCase):
    def test_extension_hitl_path(self):
        engine = MasterBillingPolicyEngine("owner-1")
        ext = MasterGovernanceExtension(engine)
        g = BillingGovernanceGuardrail("owner-1", hitl_callback=lambda c: True)
        g.attach_policy_extension(ext)
        out = g.process_input(
            OperationalInput(
                "owner-1",
                OperationType.PAYMENT_METHOD_UPDATE,
                {"provider": "stripe"},
            )
        )
        self.assertEqual(out["status"], "executed")
        self.assertEqual(out.get("policy_id"), "POL-002")

    def test_extension_hitl_denied(self):
        engine = MasterBillingPolicyEngine("owner-1")
        ext = MasterGovernanceExtension(engine)
        g = BillingGovernanceGuardrail("owner-1", hitl_callback=lambda c: False)
        g.attach_policy_extension(ext)
        out = g.process_input(
            OperationalInput(
                "owner-1",
                OperationType.FINANCIAL_TRANSACTION,
                {"amount": 1},
            )
        )
        self.assertEqual(out["status"], "rejected")
        self.assertEqual(out.get("policy_id"), "POL-002")

    def test_provisioning_auto_via_extension(self):
        engine = MasterBillingPolicyEngine("owner-1")
        ext = MasterGovernanceExtension(engine)
        g = BillingGovernanceGuardrail("owner-1", hitl_callback=lambda c: False)
        g.attach_policy_extension(ext)
        out = g.process_input(
            OperationalInput(
                "owner-1",
                OperationType.PROVISIONING_EXECUTION,
                {"plan": "pro", "action": "activate_entitlement"},
            )
        )
        self.assertEqual(out["status"], "executed")
        self.assertEqual(out.get("policy_id"), "POL-003")

    def test_as_hitl_predicate(self):
        engine = MasterBillingPolicyEngine("owner-1")
        ext = MasterGovernanceExtension(engine)
        decide = ext.as_hitl_predicate(lambda c: True)
        d = decide(
            {
                "principal_id": "owner-1",
                "operation_type": "billing_configuration",
            }
        )
        self.assertTrue(d["allowed"])
        self.assertTrue(d["detail"].get("hitl_approved"))


if __name__ == "__main__":
    unittest.main()
