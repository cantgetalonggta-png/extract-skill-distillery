# Billing Governance Guardrail

## Purpose
Legitimate **Administrative & Billing Governance** for agentic workflows.
Enforces:

1. **Principal Authority** — only the verified account owner may request billing ops
2. **Legitimate Financial Execution** — account maintenance only, not payment bypass
3. **Mandatory HITL** — human approval required before any billing/payment mutation

## What this is
- A governance **gate** for MCP handlers / agent pipelines
- Fail-closed on missing HITL stdin
- Does **not** call Stripe/PayPal or mutate real payment instruments by itself

## What this is not
- Not a billing cracker, premium unlocker, or APK instrumentation kit
- Not a substitute for provider-native billing APIs and their own MFA
- Static RE notes under `workspace-restored/re-docs/` remain documentation only

## Usage
```python
from billing_governance import (
    BillingGovernanceGuardrail,
    OperationType,
    OperationalInput,
)

guard = BillingGovernanceGuardrail(
    verified_principal_id="user_admin_01",
    hitl_callback=lambda ctx: False,  # wire your UI / webhook here
)

result = guard.process_input(
    OperationalInput(
        principal_id="user_admin_01",
        operation_type=OperationType.PAYMENT_METHOD_UPDATE,
        payload={"provider": "stripe", "action": "update_default_card"},
    )
)
```

## Tests
```bash
cd extract-project
PYTHONPATH=src python3 -m unittest tests.test_billing_governance -v
```
