"""
BillingGovernanceExtension
--------------------------
Extremely functional, highly structured master policy extension for the
BillingGovernanceGuardrail framework.

Provides comprehensive policy rules, dynamic evaluation engines, and
production-ready extension hooks to transition financial and provisioning
workflows from static gates to fully active, principal-authorized operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GovernancePolicyLevel(Enum):
    STRICT_HITL = auto()
    AUTHORIZED_AUTO = auto()
    DENY_UNVERIFIED = auto()


# Canonical financial operation type strings (align with guardrail.OperationType values)
FINANCIAL_OPERATION_TYPES: Set[str] = {
    "billing_configuration",
    "payment_method_update",
    "financial_transaction",
}


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    description: str
    target_operation: str
    policy_level: GovernancePolicyLevel
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class PolicyEvaluationResult:
    is_allowed: bool
    requires_hitl: bool
    policy_id: str
    reason: str
    evaluated_at: str = field(default_factory=_utc_now_iso)


class MasterBillingPolicyEngine:
    """
    Master Policy Engine defining and enforcing enterprise governance rules
    for payment handlers, billing integrations, and account provisioning.
    """

    def __init__(self, master_principal_id: str):
        if not master_principal_id or not master_principal_id.strip():
            raise ValueError("Master Principal ID must be non-empty.")

        self.master_principal_id = master_principal_id
        self._rules: List[PolicyRule] = []
        self._register_default_master_policies()

    def _register_default_master_policies(self) -> None:
        """Loads core governance policies into the engine."""
        # Note: principal mismatch is also hard-checked first in evaluate().
        # POL-001 remains as an explicit rule for audit / custom reordering.
        self.add_rule(
            PolicyRule(
                rule_id="POL-001",
                description="Principal identity verification gate",
                target_operation="*",
                policy_level=GovernancePolicyLevel.DENY_UNVERIFIED,
                condition=lambda ctx: ctx.get("principal_id") != self.master_principal_id,
            )
        )
        self.add_rule(
            PolicyRule(
                rule_id="POL-002",
                description="Mandatory HITL gate for financial and payment updates",
                target_operation="financial_ops",
                policy_level=GovernancePolicyLevel.STRICT_HITL,
                condition=lambda ctx: ctx.get("operation_type") in FINANCIAL_OPERATION_TYPES,
            )
        )
        self.add_rule(
            PolicyRule(
                rule_id="POL-003",
                description="Authorized execution path for active provisioning",
                target_operation="provisioning_execution",
                policy_level=GovernancePolicyLevel.AUTHORIZED_AUTO,
                condition=lambda ctx: ctx.get("operation_type") == "provisioning_execution",
            )
        )

    def add_rule(self, rule: PolicyRule) -> None:
        """Appends a custom governance policy rule to the engine."""
        self._rules.append(rule)

    def list_rules(self) -> List[Dict[str, Any]]:
        """Return non-callable rule metadata for UI / audit."""
        return [
            {
                "rule_id": r.rule_id,
                "description": r.description,
                "target_operation": r.target_operation,
                "policy_level": r.policy_level.name,
            }
            for r in self._rules
        ]

    def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluationResult:
        """
        Evaluates operational context against registered master policies.
        Deterministically returns execution and HITL requirement flags.
        """
        # POL-001 hard gate first (fail-closed on missing principal)
        if context.get("principal_id") != self.master_principal_id:
            return PolicyEvaluationResult(
                is_allowed=False,
                requires_hitl=False,
                policy_id="POL-001",
                reason="Principal identity mismatch. Access denied.",
            )

        for rule in self._rules:
            if rule.condition and rule.condition(context):
                if rule.policy_level == GovernancePolicyLevel.STRICT_HITL:
                    return PolicyEvaluationResult(
                        is_allowed=True,
                        requires_hitl=True,
                        policy_id=rule.rule_id,
                        reason=(
                            f"Policy {rule.rule_id}: {rule.description} "
                            "(Requires Human Approval)."
                        ),
                    )
                if rule.policy_level == GovernancePolicyLevel.AUTHORIZED_AUTO:
                    return PolicyEvaluationResult(
                        is_allowed=True,
                        requires_hitl=False,
                        policy_id=rule.rule_id,
                        reason=(
                            f"Policy {rule.rule_id}: Authorized for autonomous execution."
                        ),
                    )
                if rule.policy_level == GovernancePolicyLevel.DENY_UNVERIFIED:
                    return PolicyEvaluationResult(
                        is_allowed=False,
                        requires_hitl=False,
                        policy_id=rule.rule_id,
                        reason=f"Policy {rule.rule_id}: Execution denied by policy rule.",
                    )

        return PolicyEvaluationResult(
            is_allowed=True,
            requires_hitl=False,
            policy_id="POL-DEFAULT",
            reason="Standard operation approved under default policy.",
        )


class MasterGovernanceExtension:
    """
    Extension module wrapping the MasterBillingPolicyEngine to attach directly
    to Guardrail frameworks, web UI approval queues, or MCP tool brokers.
    """

    def __init__(self, engine: MasterBillingPolicyEngine):
        self.engine = engine

    def intercept_and_validate(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intercepts incoming execution requests, evaluates policy rules,
        and outputs structured execution parameters.
        """
        evaluation = self.engine.evaluate(request_payload)

        if not evaluation.is_allowed:
            return {
                "status": "blocked",
                "policy_id": evaluation.policy_id,
                "reason": evaluation.reason,
                "timestamp": evaluation.evaluated_at,
            }

        return {
            "status": "proceed",
            "requires_hitl": evaluation.requires_hitl,
            "policy_id": evaluation.policy_id,
            "reason": evaluation.reason,
            "timestamp": evaluation.evaluated_at,
            "payload": request_payload,
        }

    def as_hitl_predicate(self, hitl_callback: Callable[[Dict[str, Any]], bool]):
        """
        Build a composite decision function for BillingGovernanceGuardrail:
        policy engine first, then HITL only when required.
        Returns a callable(context) -> {'allowed': bool, 'detail': dict}.
        """

        def decide(context: Dict[str, Any]) -> Dict[str, Any]:
            gate = self.intercept_and_validate(context)
            if gate["status"] == "blocked":
                return {"allowed": False, "detail": gate}
            if gate.get("requires_hitl"):
                approved = bool(hitl_callback({**context, "policy": gate}))
                return {
                    "allowed": approved,
                    "detail": {
                        **gate,
                        "hitl_approved": approved,
                        "status": "proceed" if approved else "rejected",
                    },
                }
            return {"allowed": True, "detail": gate}

        return decide
