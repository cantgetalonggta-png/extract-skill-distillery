"""Unit tests for BillingGovernanceGuardrail."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from billing_governance import (  # noqa: E402
    BillingGovernanceError,
    BillingGovernanceGuardrail,
    OperationType,
    OperationalInput,
)


class TestBillingGovernance(unittest.TestCase):
    def test_standard_operation_auto_allows(self):
        g = BillingGovernanceGuardrail("p1", hitl_callback=lambda c: False)
        out = g.process_input(
            OperationalInput("p1", OperationType.STANDARD, {"op": "ping"})
        )
        self.assertEqual(out["status"], "success")

    def test_unauthorized_principal_raises(self):
        g = BillingGovernanceGuardrail("p1", hitl_callback=lambda c: True)
        with self.assertRaises(BillingGovernanceError):
            g.process_input(
                OperationalInput(
                    "intruder",
                    OperationType.PAYMENT_METHOD_UPDATE,
                    {"action": "update"},
                )
            )

    def test_financial_denied_by_hitl(self):
        g = BillingGovernanceGuardrail("p1", hitl_callback=lambda c: False)
        out = g.process_input(
            OperationalInput(
                "p1",
                OperationType.FINANCIAL_TRANSACTION,
                {"amount": 10, "currency": "USD"},
            )
        )
        self.assertEqual(out["status"], "rejected")

    def test_financial_approved_by_hitl(self):
        seen = {}

        def approve(ctx):
            seen.update(ctx)
            return True

        g = BillingGovernanceGuardrail("p1", hitl_callback=approve)
        out = g.process_input(
            OperationalInput(
                "p1",
                OperationType.BILLING_CONFIGURATION,
                {"plan": "pro"},
            )
        )
        self.assertEqual(out["status"], "executed")
        self.assertEqual(seen["operation_type"], "billing_configuration")
        self.assertEqual(out["operation_type"], "billing_configuration")

    def test_payment_method_update_path(self):
        g = BillingGovernanceGuardrail("admin", hitl_callback=lambda c: True)
        out = g.process_input(
            OperationalInput(
                "admin",
                OperationType.PAYMENT_METHOD_UPDATE,
                {"provider": "stripe", "last_four": "4242"},
            )
        )
        self.assertEqual(out["status"], "executed")
        self.assertIn("note", out)

    def test_empty_principal_rejected_at_init(self):
        with self.assertRaises(BillingGovernanceError):
            BillingGovernanceGuardrail("")


if __name__ == "__main__":
    unittest.main()
