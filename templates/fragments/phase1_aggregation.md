## Phase 1 Audit Fan-out and Aggregation

Phase 1 audits (security, UI/UX, data) are launched by `architecture-planner` based on the architecture document. They may all be needed, none, or any subset.

### Fan-out (T12a/b/c → auditors)
`architecture-planner`'s result flags (`security_requirements_exist`, `ui_needed`, `data_design_needed`) determine which audits run. Multiple audits can fire **simultaneously** — the orchestrator launches all matching auditors in one message (same pattern as the parallel `T45a`/`T45b` branch).

### Aggregation (auditors → T23a/b/c → architecture-planner)
Each auditor returns to `architecture-planner` via its Phase 1 transition (`T23a`/`T23b`/`T23c`). The orchestrator MUST:
1. **Collect ALL** Phase 1 auditor results before re-launching `architecture-planner` for aggregation. Do NOT re-launch arch-planner as each auditor returns — that would fork aggregation and duplicate work.
2. Track completion: `security-auditor returned`, `ui-ux returned`, `data returned`. Only when **all requested** audits have returned, re-launch `architecture-planner` with the accumulated results.
3. `architecture-planner` then aggregates and either exits via `T13` (implementation path) or `T_AGG_TO_DEVOPS` (deployment_only path).

### Deployment-only exception
When `data-engineering-architect` returns `deployment_only: true`, the data audit result still goes to `architecture-planner` (via `T23c`). Aggregation proceeds as above; the exit is `T_AGG_TO_DEVOPS` (skipping `code-implementer`, `code-reviewer`, and the test/perf branches).
