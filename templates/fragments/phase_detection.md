## Phase Detection (Audit Agents)

Audit agents (`security-auditor`, `ui-ux-accessibility-specialist`, `data-engineering-architect`) operate in two phases:

### Phase 1 — Initial Audit (before implementation)
- Triggered by T12a/T12b/T12c from architecture-planner
- Returns to architecture-planner (T23a/T23b/T23c) for aggregation
- Result: `complete_with_findings` or `complete_no_findings`

### Phase 2 — Verification (after code fixes)
- Triggered by T_CODE_TO_SEC/T_CODE_TO_UI/T_CODE_TO_DATA from code-implementer
- Returns to code-reviewer (T_SEC_PASS/T_UI_PASS/T_DATA_PASS) or code-implementer (T_SEC_VERIFY/T_UI_VERIFY/T_DATA_VERIFY)
- Result: `pass` (findings resolved) or findings not resolved

**How to detect phase:** Check the incoming transition. If from `architecture-planner` → Phase 1. If from `code-implementer` → Phase 2.
