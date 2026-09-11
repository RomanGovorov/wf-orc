## Workflow Completion

The workflow completes when `project-manager` returns `workflow_complete: true`. This happens after `tech-docs-writer` → `project-manager` (T70) AND the PM's documentation review concludes — either approved, or forced by `documentation_iteration >= max` (see workflow.yaml `iteration_counters.documentation_iteration.max`). Note that T70 itself is NOT the end: the PM may still loop back to tech-docs-writer via T70_REV.

Upon completion (PM returned `workflow_complete: true`):
- Verify PM has closed all tasks (Phase 7 of PM's methodology: backlog status → DONE, `tasks/active/` → `tasks/done/`, bulk-close UI PM if configured). Do NOT duplicate this step — PM already performed it before emitting `workflow_complete`.
- Report summary to user (including any forced-pass / blocked issues documented along the way)
- List all created artifacts
