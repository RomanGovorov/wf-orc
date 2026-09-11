## Derived Conditions (Computed by Orchestrator)

Some transition conditions are **derived** — they are not directly returned by agents but computed by the orchestrator based on workflow state.

### `no_fix_flags_present`

**Definition:** True when none of the fix completion flags are set in code-implementer's result.

**Evaluation Logic:**
```python
no_fix_flags_present = NOT (
    security_fixes_complete
    OR ui_fixes_complete
    OR data_fixes_complete
    OR test_fixes_complete
    OR perf_fixes_complete
)
```

**Use Case:** Used in T34 transition (standard pass from code-implementer to code-reviewer).

**Exception:** `blocked: true` excludes T34 — handle the BLOCKED-RESULT PROTOCOL (workflow.yaml) BEFORE evaluating transitions.

### `all_audits_complete`

**Definition:** True when all requested Phase 1 audits have returned to architecture-planner for aggregation. A data audit that returned `deployment_only: true` counts as returned (T23c fires for any Phase 1 outcome).

**Evaluation Logic:**
```python
all_audits_complete = (
    (security_audit_not_requested OR security_auditor_returned)
    AND (ui_audit_not_requested OR ui_ux_specialist_returned)
    AND (data_audit_not_requested OR data_engineer_returned)
)
```

**Use Case:** Used in T13 (implementation path) and T_AGG_TO_DEVOPS (deployment_only path) after all requested Phase 1 audits return to architecture-planner — the single aggregation point.
