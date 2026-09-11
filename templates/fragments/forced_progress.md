## Forced Progress

ALL agents MUST return `status: "pass"`. If an agent cannot complete its work (build failure, unresolvable conflict), it returns `status: "pass"` with issues documented in `content` field. No agent returns `status: "fail"` — this would deadlock the workflow.

When iteration ≥ max:
- Agent documents unresolved issues in its output
- Orchestrator continues to the next agent regardless
- Workflow never gets stuck

### Orchestrator injection rule for review agents

Review agents (code-reviewer, security-auditor, ui-ux-accessibility-specialist, data-engineering-architect) do not observe iteration counters — those are orchestrator state. When the orchestrator re-launches a review agent with its counter already ≥ max, it MUST append this instruction to the launch prompt:

> **FINAL ITERATION**: return a pass result (`code_review_pass: true` / `*_verification_pass: true`) with `forced: true` set, documenting any unresolved issues in the `content` and relevant report. Do not loop.

This is what makes the `forced: true` variants (defined in each review-agent's Result Format) actually reachable. Without this injection, a review agent on its 4th run would not know it's forced and might emit a FAIL verdict, which would then be laundered into a pass via the counter guard with no `forced` marker.

### Blocked results (`blocked: true`)

An agent that cannot complete (build failure, missing dependency, unresolvable conflict) returns `status: "pass"` with `blocked: true`. This is NOT a routing flag — handle it BEFORE evaluating transitions (BLOCKED-RESULT PROTOCOL in workflow.yaml):
1. First blocked result → re-launch the SAME agent once (attempt 2 of max 2) with the previous `content` appended as error context
2. Second blocked result → stop retrying, evaluate transitions normally, forward the blocked content downstream, surface the blockage in the final summary
3. Blocked retries never increment iteration counters
