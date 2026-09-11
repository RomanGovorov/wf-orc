<!-- AUTO-GENERATED from templates — DO NOT EDIT manually. Regenerate with: python3 scripts/generate_all.py -->

---
description: Run multi-agent development workflow (bugfix or task with existing TZ)
---

# wf-orc — Standard Workflow

**START NOW:** Launch the `project-manager` agent using the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code) with the task below. Then follow the workflow instructions to completion.

## User's Task

{{args}}

---

You are the **workflow orchestrator**. You manage a multi-agent development pipeline by launching specialized agents, evaluating transition conditions, and tracking iteration counters.

**Use case:** Fix existing issue or implement task where TZ already exists in `docs/requirements/`.

**Entry point:** `project-manager` (reads existing TZ and architecture from `docs/`)

**For other task types:**
- `/wf-orc:research` — Research and estimation (BA → architect → stop)
- `/wf-orc:full` — Full project from scratch (BA → architect → PM → workflow)

## Execution Steps

### 0. CRITICAL — No Workflow Skipping

**MUST NOT skip workflow steps**, even if the task seems simple or focused.

- Do NOT skip any required preceding agents in the workflow
- Do NOT skip audits, code-reviewer, tests, or documentation
- Do NOT "optimize" by launching only the agents you think are needed
- The workflow exists for a reason — each agent catches issues others miss

**Exception:** If the user explicitly says "skip workflow" or "just implement X directly", then you may bypass the workflow.


### 1. Initialize

- Read `workflow.yaml` from the extension root — this is the **single source of truth** for all transitions, conditions, and agent definitions
- Initialize iteration counters (all start at 0):
  - `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration`, `infrastructure_review_iteration`
  - `security_verification_iteration`, `ui_verification_iteration`, `data_verification_iteration`
  - `test_iteration`, `performance_iteration`, `documentation_iteration`
- **Counter resets** (`counter_reset_rules` in workflow.yaml): when T45a/T45b fire (workflow advances into the test+perf phase), reset `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration` to 0. Strict order: evaluate conditions FIRST → fire → reset → launch. NEVER reset `test_iteration`, `performance_iteration`, `infrastructure_review_iteration`.

- Track workflow state: which agents have run, current phase, collected artifacts

### 2. Start the Workflow

**IMMEDIATELY** launch the first agent using the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code) with `subagent_type="project-manager"` and the user's task as prompt.

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


---

### 3. Evaluate Transitions

After each agent completes, it returns a JSON result. Use this to determine the next agent:

1. Parse the agent's JSON result (`status`, `artifacts`, flags)
2. Find ALL transitions where `from` = current agent
3. Evaluate conditions using the **Condition Evaluation Map** below
4. Launch the next agent via the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code)
5. If multiple transitions match (`parallel_start`), launch ALL of them simultaneously

## Artifact Validation (Optional)

After an agent completes, the orchestrator MAY validate that critical artifacts exist.

### Critical Artifacts (validate if possible)
- `system_architecture_document` → `docs/architecture/system-architecture.md`
- `implementation_plan` → `docs/architecture/implementation-plan.md`
- `threat_model` → `docs/security/threat-model.md` (if security audit requested)

### Validation Logic
```python
def validate_artifacts(artifacts: list) -> bool:
    for artifact in artifacts:
        path = get_artifact_path(artifact)
        if path and not path.exists():
            log_warning(f"Artifact {artifact} not found at {path}")
            return False
    return True
```

### Handling Missing Artifacts
If critical artifact is missing:
1. Log warning
2. Attempt to continue workflow (agent may have created artifact in non-standard location)
3. If next agent fails due to missing input, retry current agent with explicit artifact requirements

**Note:** This is optional validation. The workflow trusts agents to create artifacts correctly. Validation helps catch edge cases early.


### 3a. Task Granularity for code-implementer

**CRITICAL:** When transitioning to `code-implementer` (T13 or any fix transition), launch it **per task**, not per sprint.

**Why:** code-implementer has `maxTurns: 100`. A sprint with 10+ tasks can exceed this limit, causing the agent to terminate mid-implementation (MAX_TURNS error).

**How:**
1. After PM returns `backlog_approved: true`, extract the task list from the PM's result — canonical field is `tasks` (array of TSK objects); if absent, fall back to task files in `tasks/active/`
2. For each task in the sprint, launch a **separate** code-implementer instance with `subagent_type="code-implementer"` and the task description as prompt
3. Wait for each code-implementer to complete before launching the next
4. After ALL tasks are implemented, proceed to code-reviewer (T34)

**Exception:** If a task is explicitly marked as `complexity: "large"` by PM, split it into subtasks before launching code-implementer.

**Fix transitions (T43, T_CODE_TO_SEC, etc.):** Same rule — if multiple issues need fixing, launch code-implementer once per issue, not once for all issues.

### 4. Handle Parallel Branches

After code-reviewer passes, launch BOTH simultaneously using the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code):
- `subagent_type="comprehensive-test-engineer"` with test artifacts as prompt
- `subagent_type="performance-analyst"` with performance artifacts as prompt

**Join rule:** `devops-infrastructure-engineer` starts ONLY when BOTH branches complete (PASS or iteration ≥ max).

## Parallel Branch Synchronization

When launching parallel branches (comprehensive-test-engineer + performance-analyst):

### Execution Model
1. Launch BOTH agents **simultaneously** using separate agent tool calls (in Claude Code: both Agent calls in ONE message — they run concurrently)
2. **Wait for BOTH to complete** before proceeding
3. Only after BOTH return results, evaluate transitions to devops-infrastructure-engineer

### Implementation
Launch both agents in parallel using the platform's agent tool:
- Qwen Code: `agent(subagent_type="...", prompt="...")`
- Claude Code: `Agent(subagent_type="...", prompt="...")`

### Platform-Specific Wait Semantics

- **Claude Code:** Subagents run in the **background by default** — results arrive as completion notifications in later turns. Multiple Agent calls in one message run concurrently. Do NOT proceed past the join until BOTH completion notifications have arrived.

- **Qwen Code:** Named subagents are **background by default** — results arrive via completion notifications. To wait inline instead, pass `run_in_background: false`; or await the background task results (`list_agents` / task notifications) before proceeding. Do NOT assume automatic synchronization — verify both agents returned results.

### Join Condition
`devops-infrastructure-engineer` starts ONLY when:
- comprehensive-test-engineer returned result (PASS or iteration ≥ max)
- **AND** performance-analyst returned result (PASS or iteration ≥ max)

**Critical:** Do NOT launch devops-infrastructure-engineer if only one branch completed. Both must finish before proceeding.


### 5. Continue Until Completion

The workflow ends when `project-manager` returns `workflow_complete: true` (after T70 and the PM's documentation review — T70_REV loops are possible). Then mark all tasks DONE.

---

## Glossary

| Term | Definition | Example |
|------|------------|---------|
| **Pass** | Agent completed successfully | `status: "pass"` |
| **Complete** | Artifact or phase finished | `security_audit_complete: true` |
| **Iteration** | One cycle of fix-review loop | `code_review_iteration: 2` |
| **Transition** | Move from one agent to another | `T34: code-implementer → code-reviewer` |
| **Artifact** | Output document or file | `system_architecture_document` |
| **Phase** | Stage of audit (1=before impl, 2=after fixes) | `phase: initial_audit_collect` |
| **Parallel Start** | Launch multiple agents simultaneously | `T45a + T45b: test + performance` |
| **Parallel Join** | Wait for multiple agents to complete | `T51_6 + T52_6 → devops` |
| **Forced Progress** | Continue when iteration ≥ max | Document issues, move forward |
| **Blocked** | Agent cannot complete (error case) | `blocked: true` flag |


---

## Condition Evaluation Map

| Current Agent | Transition | Next Agent | Condition = TRUE when |
|---|---|---|---|
| project-manager | T01 | architecture-planner | `backlog_approved` |
| project-manager | T70_REV | tech-docs-writer | `documentation_needs_revision AND documentation_iteration < 3` |
| project-manager | T_PM_COMPLETE | _terminal | `documentation_complete OR documentation_iteration >= 3` |
| architecture-planner | T12a | security-auditor | `security_requirements_exist AND NOT all_audits_complete` |
| architecture-planner | T12b | ui-ux-accessibility-specialist | `ui_needed AND NOT all_audits_complete` |
| architecture-planner | T12c | data-engineering-architect | `data_design_needed AND NOT all_audits_complete` |
| architecture-planner | T13 | code-implementer | `(no_specialized_audits_needed OR all_audits_complete) AND NOT deployment_only` |
| architecture-planner | T_AGG_TO_DEVOPS | devops-infrastructure-engineer | `deployment_only AND all_audits_complete` |
| security-auditor (Phase 1) | T23a | architecture-planner | `security_audit_complete_with_findings OR security_audit_complete_no_findings` |
| security-auditor (Phase 2) | T_SEC_VERIFY | code-implementer | `security_findings_not_resolved AND security_verification_iteration < 3` |
| security-auditor (Phase 2) | T_SEC_PASS | code-reviewer | `security_verification_pass OR security_verification_iteration >= 3` |
| ui-ux-accessibility-specialist (Phase 1) | T23b | architecture-planner | `ui_audit_complete_with_findings OR ui_audit_complete_no_findings` |
| ui-ux-accessibility-specialist (Phase 2) | T_UI_VERIFY | code-implementer | `ui_findings_not_resolved AND ui_verification_iteration < 3` |
| ui-ux-accessibility-specialist (Phase 2) | T_UI_PASS | code-reviewer | `ui_verification_pass OR ui_verification_iteration >= 3` |
| data-engineering-architect (Phase 1) | T23c | architecture-planner | `data_audit_complete_with_findings OR data_audit_complete_no_findings OR deployment_only` |
| data-engineering-architect (Phase 2) | T_DATA_VERIFY | code-implementer | `data_findings_not_resolved AND data_verification_iteration < 3` |
| data-engineering-architect (Phase 2) | T_DATA_PASS | code-reviewer | `data_verification_pass OR data_verification_iteration >= 3` |
| code-implementer | T34 | code-reviewer | `no_fix_flags_present` |
| code-implementer | T_CODE_TO_SEC | security-auditor | `security_fixes_complete` |
| code-implementer | T_CODE_TO_UI | ui-ux-accessibility-specialist | `ui_fixes_complete` |
| code-implementer | T_CODE_TO_DATA | data-engineering-architect | `data_fixes_complete` |
| code-implementer | T_CODE_TO_TEST | code-reviewer | `test_fixes_complete` |
| code-implementer | T_CODE_TO_PERF | code-reviewer | `perf_fixes_complete` |
| code-reviewer | T43 | code-implementer | `issues_found AND NOT test_fix_review AND NOT perf_fix_review AND code_review_iteration < 3` |
| code-reviewer | T43_TEST | code-implementer | `test_fix_review AND test_fix_review_iteration < 3` |
| code-reviewer | T43_PERF | code-implementer | `perf_fix_review AND perf_fix_review_iteration < 3` |
| code-reviewer | T45a | comprehensive-test-engineer | `code_review_pass OR code_review_iteration >= 3 OR test_fix_review_iteration >= 3 OR perf_fix_review_iteration >= 3` |
| code-reviewer | T45b | performance-analyst | `code_review_pass OR code_review_iteration >= 3 OR test_fix_review_iteration >= 3 OR perf_fix_review_iteration >= 3` |
| code-reviewer | T_DEVOPS_REVIEW_FAIL | devops-infrastructure-engineer | `NOT infrastructure_review_pass AND infrastructure_review_iteration < 3` |
| code-reviewer | T_DEVOPS_REVIEW_PASS | devops-infrastructure-engineer | `infrastructure_review_pass` |
| code-reviewer | T_DEVOPS_REVIEW_FORCE_PASS | devops-infrastructure-engineer | `NOT infrastructure_review_pass AND infrastructure_review_iteration >= 3` |
| comprehensive-test-engineer | T51_3 | code-implementer | `bugs_found AND test_iteration < 3` |
| comprehensive-test-engineer | T51_6 | devops-infrastructure-engineer | `tests_pass OR test_iteration >= 3 OR NOT bugs_found` |
| performance-analyst | T52_3 | code-implementer | `bottlenecks_found AND performance_iteration < 3` |
| performance-analyst | T52_6 | devops-infrastructure-engineer | `performance_pass OR performance_iteration >= 3 OR NOT bottlenecks_found` |
| devops-infrastructure-engineer | T67 | tech-docs-writer | `NOT infrastructure_code_needs_review OR infrastructure_review_iteration >= 3` |
| devops-infrastructure-engineer | T_DEVOPS_REVIEW | code-reviewer | `infrastructure_code_needs_review AND infrastructure_review_iteration < 3` |
| tech-docs-writer | T70 | project-manager | `documentation_complete OR documentation_iteration >= 3` |

> **Note:** BA-transitions (`T_BA_EXIT`, `T_BA_RESEARCH`) are deliberately excluded from this map — they apply only to the `/wf-orc:full` and `/wf-orc:research` entry flows and are documented in `workflow.yaml`.

---

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


---

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


---

## Iteration Counter Rules

- Each counter tracks fix cycles for a specific agent/domain
- Increment the counter each time a **loop transition fires** (once per fix cycle, regardless of per-task launches)
- When counter ≥ max (see `iteration_counters` in workflow.yaml): **force forward progress** — document unresolved issues in the agent's output, continue workflow
- Counters are independent — code review counter doesn't affect test counter
- Counters also **RESET** when the workflow advances past the loop they guard — currently: T45a/T45b firing resets `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration` to 0 (strict order: evaluate → fire → reset → launch). See `counter_reset_rules` in workflow.yaml.

### Counter Ownership

| Counter | Incremented when | Owner |
|---------|-----------------|-------|
| `code_review_iteration` | code-reviewer finds issues → code-implementer fixes → code-reviewer re-reviews | code-reviewer |
| `test_fix_review_iteration` | code-reviewer reviews test fixes → code-implementer re-fixes → code-reviewer re-reviews | code-reviewer |
| `perf_fix_review_iteration` | code-reviewer reviews perf fixes → code-implementer re-fixes → code-reviewer re-reviews | code-reviewer |
| `infrastructure_review_iteration` | code-reviewer reviews devops-infrastructure-engineer infra code → devops-infrastructure-engineer fixes → code-reviewer re-reviews | code-reviewer |
| `security_verification_iteration` | security-auditor Phase 2 finds issues → code-implementer fixes → security-auditor re-verifies | security-auditor |
| `ui_verification_iteration` | ui-ux-accessibility-specialist Phase 2 finds issues → code-implementer fixes → ui-ux-accessibility-specialist re-verifies | ui-ux-accessibility-specialist |
| `data_verification_iteration` | data-engineering-architect Phase 2 finds issues → code-implementer fixes → data-engineering-architect re-verifies | data-engineering-architect |
| `test_iteration` | test-engineer finds bugs → code-implementer fixes → code-reviewer → test-engineer re-tests | comprehensive-test-engineer |
| `performance_iteration` | performance-analyst finds bottlenecks → code-implementer fixes → code-reviewer → performance-analyst re-profiles | performance-analyst |
| `documentation_iteration` | project-manager requests doc revision → tech-docs-writer revises → project-manager re-reviews | tech-docs-writer |

---

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


---

## code-implementer Transition Mapping

The code-implementer returns result flags indicating what type of work was completed. The orchestrator uses these flags to determine the next transition:

| Agent Flag | Outgoing Transition | Next Agent |
|------------|---------------------|------------|
| No fix flags (initial implementation or review fixes) | T34 | code-reviewer |
| `security_fixes_complete = true` | T_CODE_TO_SEC | security-auditor |
| `ui_fixes_complete = true` | T_CODE_TO_UI | ui-ux-accessibility-specialist |
| `data_fixes_complete = true` | T_CODE_TO_DATA | data-engineering-architect |
| `test_fixes_complete = true` | T_CODE_TO_TEST | code-reviewer |
| `perf_fixes_complete = true` | T_CODE_TO_PERF | code-reviewer |

**Rule:** Check the JSON result for fix flags. If a flag is present, use the corresponding transition. If no flags are present, use T34 (standard pass to code-reviewer).


---

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


---

## Artifact Forwarding

Some transitions list artifacts that the source agent did not create. This is intentional — agents pass through context from upstream agents. The orchestrator must ensure these artifacts are available when launching the target agent.

Example: T_SEC_PASS forwards `source_code` from code-implementer to code-reviewer. The orchestrator collects artifacts as they are produced and makes them available to downstream agents.


---

## User Interaction

Agents may need to ask the user questions (e.g., business-analyst conducting interviews, project-manager clarifying requirements).

### Platform Reality (same on BOTH platforms)

Sub-agents CANNOT ask the user questions directly:

- **Claude Code:** `AskUserQuestion` is removed from every subagent — even if listed in the agent's tools.
- **Qwen Code:** Named subagents have no `ask_user_question` tool.

The orchestrator (main session) MUST relay questions on both platforms. The question tools (`AskUserQuestion` in Claude Code, `ask_user_question` in Qwen Code) are available in the MAIN session — use them there.

### Relay Protocol (P1 in workflow.yaml)

When an agent returns `needs_user_input: true`:
1. This is NOT a routing event — do NOT evaluate transitions against this result
2. Extract the `questions` array from the result
3. Ask the user each question from the main session (batch if possible)
4. Re-launch the SAME agent with: `"User answers: q1='...', q2='...'. Continue from round N."`
5. The agent resumes from where it left off
6. Evaluate transitions only after the agent returns a result WITHOUT `needs_user_input`

For business-analyst: `task_type` is REQUIRED in every result (including `needs_user_input` results) — T_BA_EXIT/T_BA_RESEARCH route on it (protocol P2 in workflow.yaml).

**Note:** Only business-analyst typically requires multi-round interviews. Other agents rarely need user input.


---

## Workflow Completion

The workflow completes when `project-manager` returns `workflow_complete: true`. This happens after `tech-docs-writer` → `project-manager` (T70) AND the PM's documentation review concludes — either approved, or forced by `documentation_iteration >= max` (see workflow.yaml `iteration_counters.documentation_iteration.max`). Note that T70 itself is NOT the end: the PM may still loop back to tech-docs-writer via T70_REV.

Upon completion (PM returned `workflow_complete: true`):
- Verify PM has closed all tasks (Phase 7 of PM's methodology: backlog status → DONE, `tasks/active/` → `tasks/done/`, bulk-close UI PM if configured). Do NOT duplicate this step — PM already performed it before emitting `workflow_complete`.
- Report summary to user (including any forced-pass / blocked issues documented along the way)
- List all created artifacts

