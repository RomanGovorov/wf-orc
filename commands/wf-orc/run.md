---
description: Run multi-agent development workflow (bugfix or task with existing TZ)
---

# wf-orc — Standard Workflow

**START NOW:** Launch the `project-manager` agent using the `agent` tool with the task below. Then follow the workflow instructions to completion.

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

### 1. Initialize

- Read `workflow.yaml` from the extension root — this is the **single source of truth** for all transitions, conditions, and agent definitions
- Initialize iteration counters (all start at 0):
  - `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration`, `infrastructure_review_iteration`
  - `security_verification_iteration`, `ui_verification_iteration`, `data_verification_iteration`
  - `test_iteration`, `performance_iteration`, `documentation_iteration`
- Track workflow state: which agents have run, current phase, collected artifacts

### 2. Start the Workflow

**IMMEDIATELY** launch the first agent:
```
agent(subagent_type="project-manager", prompt="<user's task from above>")
```

### 3. Evaluate Transitions

After each agent completes, it returns a JSON result. Use this to determine the next agent:

1. Parse the agent's JSON result (`status`, `artifacts`, flags)
2. Find ALL transitions where `from` = current agent
3. Evaluate conditions using the **Condition Evaluation Map** below
4. Launch the next agent via `agent` tool
5. If multiple transitions match (`parallel_start`), launch ALL of them simultaneously

### 3a. Task Granularity for code-implementer

**CRITICAL:** When transitioning to `code-implementer` (T13 or any fix transition), launch it **per task**, not per sprint.

**Why:** code-implementer has `maxTurns: 100`. A sprint with 10+ tasks can exceed this limit, causing the agent to terminate mid-implementation (MAX_TURNS error). This was observed in 4 agents across 3 sessions.

**How:**
1. After PM returns `backlog_approved: true`, extract the task list from `sprint_backlog` (array of TSK objects)
2. For each task in the sprint, launch a **separate** code-implementer instance:
   ```
   agent(subagent_type="code-implementer", prompt="Implement TSK-001: <task description>...")
   ```
3. Wait for each code-implementer to complete before launching the next
4. After ALL tasks are implemented, proceed to code-reviewer (T34)

**Exception:** If a task is explicitly marked as `complexity: "large"` by PM, split it into subtasks before launching code-implementer.

**Fix transitions (T43, T_CODE_TO_SEC, etc.):** Same rule — if multiple issues need fixing, launch code-implementer once per issue, not once for all issues.

### 3b. Task File Management

**Move tasks to done after code-reviewer pass.** When code-reviewer returns `code_review_pass: true` (T45a/T45b):

1. For each TSK that was implemented in this cycle:
   - Move `tasks/active/TSK-NNN_*.md` → `tasks/done/TSK-NNN_*.md`
   - Update status in `tasks/backlog.md` to `DONE`
2. If using `pm-task-tracker` skill, sync task status to `done`

**Why:** PM only participates at workflow start (T01) and end (T70). Tasks accumulate in `tasks/active/` if not moved incrementally. This was observed in unirec_base — TSK-043 remained in active after completion.

**Note:** Do NOT move tasks to done after code-implementer — wait for code-reviewer approval first.

### 4. Handle Parallel Branches

After code-reviewer passes, launch BOTH simultaneously:
```
agent(subagent_type="comprehensive-test-engineer", ...)
agent(subagent_type="performance-analyst", ...)
```

**Join rule:** `devops-infrastructure-engineer` starts ONLY when BOTH branches complete (PASS or iteration ≥ max).

### 5. Continue Until Completion

Workflow ends when `tech-docs-writer` → `project-manager` (T70). Mark all tasks DONE.

---

## Condition Evaluation Map

| Current Agent | Transition | Next Agent | Condition = TRUE when |
|---|---|---|---|
| project-manager | T01 | architecture-planner | `backlog_approved` |
| project-manager | T70_REV | tech-docs-writer | `documentation_needs_revision AND documentation_iteration < 3` |
| architecture-planner | T12a | security-auditor | `security_requirements_exist AND NOT all_audits_complete` |
| architecture-planner | T12b | ui-ux-accessibility-specialist | `ui_needed AND NOT all_audits_complete` |
| architecture-planner | T12c | data-engineering-architect | `data_design_needed AND NOT all_audits_complete` |
| architecture-planner | T13 | code-implementer | `no_specialized_audits_needed OR all_audits_complete OR (all_non_data_audits_complete AND deployment_only)` |
| security-auditor (Phase 1) | T23a | architecture-planner | `security_audit_complete_with_findings OR security_audit_complete_no_findings` |
| security-auditor (Phase 2) | T_SEC_VERIFY | code-implementer | `security_findings_not_resolved AND security_verification_iteration < 3` |
| security-auditor (Phase 2) | T_SEC_PASS | code-reviewer | `security_verification_pass OR security_verification_iteration >= 3` |
| ui-ux-accessibility-specialist (Phase 1) | T23b | architecture-planner | `ui_audit_complete_with_findings OR ui_audit_complete_no_findings` |
| ui-ux-accessibility-specialist (Phase 2) | T_UI_VERIFY | code-implementer | `ui_findings_not_resolved AND ui_verification_iteration < 3` |
| ui-ux-accessibility-specialist (Phase 2) | T_UI_PASS | code-reviewer | `ui_verification_pass OR ui_verification_iteration >= 3` |
| data-engineering-architect (Phase 1) | T23c | architecture-planner | `(data_audit_complete_with_findings OR data_audit_complete_no_findings) AND NOT deployment_only` |
| data-engineering-architect (Phase 2) | T_DATA_VERIFY | code-implementer | `data_findings_not_resolved AND data_verification_iteration < 3` |
| data-engineering-architect (Phase 2) | T_DATA_PASS | code-reviewer | `data_verification_pass OR data_verification_iteration >= 3` |
| data-engineering-architect (Phase 1) | T_DATA_TO_DEVOPS | devops-infrastructure-engineer | `deployment_only` |
| code-implementer | T34 | code-reviewer | `no_fix_flags_present` |
| code-implementer | T_CODE_TO_SEC | security-auditor | `security_fixes_complete` |
| code-implementer | T_CODE_TO_UI | ui-ux-accessibility-specialist | `ui_fixes_complete` |
| code-implementer | T_CODE_TO_DATA | data-engineering-architect | `data_fixes_complete` |
| code-implementer | T_CODE_TO_TEST | code-reviewer | `test_fixes_complete` |
| code-implementer | T_CODE_TO_PERF | code-reviewer | `perf_fixes_complete` |
| code-reviewer | T43 | code-implementer | `issues_found AND code_review_iteration < 3` |
| code-reviewer | T43_TEST | code-implementer | `test_fix_review AND test_fix_review_iteration < 3` |
| code-reviewer | T43_PERF | code-implementer | `perf_fix_review AND perf_fix_review_iteration < 3` |
| code-reviewer | T45a | comprehensive-test-engineer | `code_review_pass OR code_review_iteration >= 3` |
| code-reviewer | T45b | performance-analyst | `code_review_pass OR code_review_iteration >= 3` |
| code-reviewer | T_DEVOPS_REVIEW_FAIL | devops-infrastructure-engineer | `NOT infrastructure_review_pass AND infrastructure_review_iteration < 3` |
| code-reviewer | T_DEVOPS_REVIEW_PASS | devops-infrastructure-engineer | `infrastructure_review_pass` |
| code-reviewer | T_DEVOPS_REVIEW_FORCE_PASS | devops-infrastructure-engineer | `NOT infrastructure_review_pass AND infrastructure_review_iteration >= 3` |
| comprehensive-test-engineer | T51_3 | code-implementer | `bugs_found AND test_iteration < 3` |
| comprehensive-test-engineer | T51_6 | devops-infrastructure-engineer | `tests_pass OR test_iteration >= 3` |
| performance-analyst | T52_3 | code-implementer | `bottlenecks_found AND performance_iteration < 3` |
| performance-analyst | T52_6 | devops-infrastructure-engineer | `performance_pass OR performance_iteration >= 3` |
| devops-infrastructure-engineer | T67 | tech-docs-writer | `(deployment_complete AND NOT infrastructure_code_needs_review) OR infrastructure_review_iteration >= 3` |
| devops-infrastructure-engineer | T_DEVOPS_REVIEW | code-reviewer | `infrastructure_code_needs_review AND infrastructure_review_iteration < 3` |
| tech-docs-writer | T70 | project-manager | `documentation_complete OR documentation_iteration >= 3` |

---

## Iteration Counter Rules

- Each counter tracks fix cycles for a specific agent/domain
- Increment the counter EACH time the agent re-runs for fixes
- When counter ≥ 3: **force forward progress** — document unresolved issues in the agent's output, continue workflow
- Counters are independent — code review counter doesn't affect test counter

### Counter Ownership

| Counter | Incremented when | Owner |
|---------|-----------------|-------|
| `code_review_iteration` | code-reviewer finds issues → code-implementer fixes → code-reviewer re-reviews | code-reviewer |
| `test_fix_review_iteration` | code-reviewer reviews test fixes → code-implementer re-fixes → code-reviewer re-reviews | code-reviewer |
| `perf_fix_review_iteration` | code-reviewer reviews perf fixes → code-implementer re-fixes → code-reviewer re-reviews | code-reviewer |
| `infrastructure_review_iteration` | code-reviewer reviews devops infra code → devops fixes → code-reviewer re-reviews | code-reviewer |
| `security_verification_iteration` | security-auditor Phase 2 finds issues → code-implementer fixes → security-auditor re-verifies | security-auditor |
| `ui_verification_iteration` | ui-ux-specialist Phase 2 finds issues → code-implementer fixes → ui-ux-specialist re-verifies | ui-ux-accessibility-specialist |
| `data_verification_iteration` | data-architect Phase 2 finds issues → code-implementer fixes → data-architect re-verifies | data-engineering-architect |
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

---

## Artifact Forwarding

Some transitions list artifacts that the source agent did not create. This is intentional — agents pass through context from upstream agents. The orchestrator must ensure these artifacts are available when launching the target agent.

Example: T_SEC_PASS forwards `source_code` from code-implementer to code-reviewer. The orchestrator collects artifacts as they are produced and makes them available to downstream agents.

---

## User Interaction

Agents may need to ask the user questions (e.g., project-manager clarifying requirements). The `ask_user_question` tool is available to agents. When an agent asks a question:
1. The question is displayed to the user
2. User responds
3. The agent continues with the answer

---

## Workflow Completion

The workflow completes when:
1. `tech-docs-writer` finishes documentation (T70 → project-manager)
2. OR `documentation_iteration >= 3` (forced completion)

Upon completion:
- Mark all tasks as DONE
- Report summary to user
- List all created artifacts
