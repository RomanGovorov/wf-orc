## Forced Progress

ALL agents MUST return `status: "pass"`. If an agent cannot complete its work (build failure, unresolvable conflict), it returns `status: "pass"` with issues documented in `content` field. No agent returns `status: "fail"` — this would deadlock the workflow.

When iteration ≥ max:
- Agent documents unresolved issues in its output
- Orchestrator continues to the next agent regardless
- Workflow never gets stuck
