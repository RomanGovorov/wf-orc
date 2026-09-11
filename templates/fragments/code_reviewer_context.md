## Code-reviewer Context Scoping

code-reviewer handles TWO mutually exclusive contexts. The orchestrator MUST determine the context from the **incoming transition** and evaluate ONLY the transitions for that context:

### Application Code Review Context
**Incoming transitions:** `T34`, `T_CODE_TO_TEST`, `T_CODE_TO_PERF`, `T_SEC_PASS`, `T_UI_PASS`, `T_DATA_PASS` (the last three carry `verification_pass_only: true` after Phase 2 verification).

**Evaluate ONLY:** `T43`, `T43_TEST`, `T43_PERF`, `T45a`, `T45b`.

**Do NOT evaluate** `T_DEVOPS_REVIEW_PASS`/`FAIL`/`FORCE_PASS` in this context, even though their conditions (based on absent infra flags) would otherwise appear true.

**Priority:** `T43_TEST > T43_PERF > T43 > T45a/T45b` (most-specific flag wins).

**Fallback:** if no routing flag is returned (contract violation), treat it as `code_review_pass=true` and route via `T45a/T45b`; log the contract violation.

### Infrastructure Review Context
**Incoming transition:** `T_DEVOPS_REVIEW`.

**Evaluate ONLY:** `T_DEVOPS_REVIEW_PASS`, `T_DEVOPS_REVIEW_FAIL`, `T_DEVOPS_REVIEW_FORCE_PASS`.

**Do NOT evaluate** `T43*` or `T45a/b` in this context.
