"""
BillingGovernanceGuardrail
--------------------------
A structured Python module implementing the Administrative & Billing Governance
Directive for agentic workflows, Model Context Protocol (MCP) handlers, or
automated financial execution pipelines.

Core Principles Enforced:
1. Principal Authority & Account Ownership
2. Legitimate Financial Execution (Account Maintenance)
3. Mandatory Human Approval Protocol (HITL Interception)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("BillingGovernance")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OperationType(Enum):
    STANDARD = "standard"
    BILLING_CONFIGURATION = "billing_configuration"
    PAYMENT_METHOD_UPDATE = "payment_method_update"
    FINANCIAL_TRANSACTION = "financial_transaction"
    PROVISIONING_EXECUTION = "provisioning_execution"


@dataclass
class OperationalInput:
    principal_id: str
    operation_type: OperationType
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=_utc_now_iso)


class BillingGovernanceError(Exception):
    """Raised when governance rules or human approval protocols are violated."""


class BillingGovernanceGuardrail:
    """
    Enforces governance boundaries for agentic systems handling billing,
    payment instruments, and account configurations.
    """

    def __init__(
        self,
        verified_principal_id: str,
        hitl_callback: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ):
        if not verified_principal_id or not str(verified_principal_id).strip():
            raise BillingGovernanceError("verified_principal_id is required.")
        self.verified_principal_id = verified_principal_id
        self.hitl_callback = hitl_callback or self._default_hitl_prompt
        self.policy_extension = None  # optional MasterGovernanceExtension
        logger.info(
            "BillingGovernanceGuardrail initialized for Principal: %s",
            self.verified_principal_id,
        )

    def attach_policy_extension(self, extension: "MasterGovernanceExtension") -> None:
        """Attach MasterGovernanceExtension for pre-HITL policy evaluation."""
        self.policy_extension = extension
        logger.info("MasterGovernanceExtension attached to guardrail.")

    def _default_hitl_prompt(self, action_payload: Dict[str, Any]) -> bool:
        """
        Default Mandatory Human-In-The-Loop (HITL) Interception mechanism.
        In production, map this to an interactive UI, CLI confirmation, or
        secure webhook. Default is FAIL-CLOSED when stdin is non-interactive.
        """
        print("\n" + "=" * 60)
        print("[MANDATORY HITL INTERCEPTION - PENDING HUMAN APPROVAL]")
        print(f"Timestamp: {_utc_now_iso()}")
        print(f"Operation Type: {action_payload.get('operation_type')}")
        print(f"Payload Details: {action_payload.get('payload')}")
        print("=" * 60)

        try:
            response = input(
                "Authorize this financial/billing operation? (yes/no): "
            ).strip().lower()
        except EOFError:
            logger.warning("HITL stdin unavailable; defaulting to DENY (fail-closed).")
            return False
        return response in {"yes", "y", "true", "1"}

    def process_input(self, operational_input: OperationalInput) -> Dict[str, Any]:
        """
        Processes an incoming operational request, verifying principal authority
        and enforcing mandatory human approval for financial configurations.
        """
        if operational_input.principal_id != self.verified_principal_id:
            logger.error(
                "Principal verification failed for ID: %s",
                operational_input.principal_id,
            )
            raise BillingGovernanceError("Unauthorized principal ID provided.")

        logger.info("Principal authority verified for %s.", self.verified_principal_id)

        approval_context = {
            "principal_id": operational_input.principal_id,
            "operation_type": operational_input.operation_type.value,
            "payload": operational_input.payload,
            "timestamp": operational_input.timestamp,
        }

        # Optional master policy engine path (covers provisioning + financial)
        if self.policy_extension is not None:
            gate = self.policy_extension.intercept_and_validate(approval_context)
            if gate["status"] == "blocked":
                logger.warning("Policy blocked operation: %s", gate.get("reason"))
                return {
                    "status": "blocked",
                    "reason": gate.get("reason"),
                    "policy_id": gate.get("policy_id"),
                    "timestamp": _utc_now_iso(),
                }
            if gate.get("requires_hitl"):
                logger.info(
                    "Policy %s requires HITL for %s",
                    gate.get("policy_id"),
                    operational_input.operation_type.value,
                )
                is_approved = self.hitl_callback({**approval_context, "policy": gate})
                if not is_approved:
                    logger.warning("HITL denied after policy proceed.")
                    return {
                        "status": "rejected",
                        "reason": "Human approval explicitly denied or not provided.",
                        "policy_id": gate.get("policy_id"),
                        "timestamp": _utc_now_iso(),
                    }
                logger.info("HITL granted after policy proceed.")
                result = self._execute_authorized_operation(operational_input)
                result["policy_id"] = gate.get("policy_id")
                return result
            # AUTHORIZED_AUTO or default proceed without HITL
            logger.info(
                "Policy %s authorized auto path for %s",
                gate.get("policy_id"),
                operational_input.operation_type.value,
            )
            if operational_input.operation_type in {
                OperationType.BILLING_CONFIGURATION,
                OperationType.PAYMENT_METHOD_UPDATE,
                OperationType.FINANCIAL_TRANSACTION,
            } or operational_input.operation_type.value == "provisioning_execution":
                result = self._execute_authorized_operation(operational_input)
                result["policy_id"] = gate.get("policy_id")
                result["policy_reason"] = gate.get("reason")
                return result
            return {
                "status": "success",
                "message": "Standard operation processed under master policy.",
                "policy_id": gate.get("policy_id"),
                "timestamp": _utc_now_iso(),
            }

        # Legacy path (no extension): financial ops always HITL
        if operational_input.operation_type in {
            OperationType.BILLING_CONFIGURATION,
            OperationType.PAYMENT_METHOD_UPDATE,
            OperationType.FINANCIAL_TRANSACTION,
        }:
            logger.info(
                "Financial/Billing operation detected (%s). Pausing for human confirmation.",
                operational_input.operation_type.value,
            )
            is_approved = self.hitl_callback(approval_context)
            if not is_approved:
                logger.warning(
                    "Billing operation rejected or ignored by human principal."
                )
                return {
                    "status": "rejected",
                    "reason": "Human approval explicitly denied or not provided.",
                    "timestamp": _utc_now_iso(),
                }
            logger.info("Human approval granted. Executing legitimate financial operation.")
            return self._execute_authorized_operation(operational_input)

        return {
            "status": "success",
            "message": "Standard operation processed without financial triggers.",
            "timestamp": _utc_now_iso(),
        }

    def _execute_authorized_operation(
        self, operational_input: OperationalInput
    ) -> Dict[str, Any]:
        """
        Records an authorized transaction or configuration update.
        Downstream payment APIs are intentionally not called here — this module
        is a governance gate, not a payment processor.
        """
        logger.info("Executing operation: %s", operational_input.operation_type.value)
        return {
            "status": "executed",
            "principal_id": operational_input.principal_id,
            "operation_type": operational_input.operation_type.value,
            "execution_timestamp": _utc_now_iso(),
            "note": "Governance gate passed; no external payment API invoked.",
        }


if __name__ == "__main__":
    # Demo only: auto-deny HITL so this never hangs in non-interactive agents.
    guardrail = BillingGovernanceGuardrail(
        verified_principal_id="user_admin_01",
        hitl_callback=lambda _ctx: False,
    )
    sample_request = OperationalInput(
        principal_id="user_admin_01",
        operation_type=OperationType.PAYMENT_METHOD_UPDATE,
        payload={
            "provider": "stripe",
            "last_four": "4242",
            "action": "update_default_card",
        },
    )
    try:
        result = guardrail.process_input(sample_request)
        print("\nExecution Result:", result)
    except Exception as e:
        print(f"\nGovernance Exception Caught: {e}")
