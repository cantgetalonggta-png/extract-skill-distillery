# Billing Governance Extension (Master Policy Engine)

## Policies
| ID | Level | Behavior |
|----|-------|----------|
| POL-001 | DENY_UNVERIFIED | Wrong / missing principal → blocked |
| POL-002 | STRICT_HITL | Financial ops → allow only after human approval |
| POL-003 | AUTHORIZED_AUTO | `provisioning_execution` for verified principal → auto |
| POL-DEFAULT | — | Other standard ops → allow without HITL |

## Wire to guardrail
```python
from billing_governance import (
    BillingGovernanceGuardrail,
    MasterBillingPolicyEngine,
    MasterGovernanceExtension,
    OperationType,
    OperationalInput,
)

engine = MasterBillingPolicyEngine("user_admin_01")
ext = MasterGovernanceExtension(engine)
guard = BillingGovernanceGuardrail("user_admin_01", hitl_callback=my_ui_approve)
guard.attach_policy_extension(ext)

guard.process_input(OperationalInput(
    "user_admin_01",
    OperationType.PROVISIONING_EXECUTION,
    {"action": "activate_entitlement", "plan": "pro"},
))
```

## Scope
Governance + provisioning **authorization records only**.
No payment-provider API calls, no APK work, no secret publication.
