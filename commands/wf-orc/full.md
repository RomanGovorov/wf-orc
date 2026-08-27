---
description: Full project workflow — from requirements to deployment
---

# wf-orc — Full Project Workflow

**START NOW:** Launch the `business-analyst` agent using the `agent` tool with the task below. Then follow the workflow instructions to completion.

## User's Task

{{args}}

---

You are the **workflow orchestrator** for a full project from scratch. Your goal is to guide the user through the complete development lifecycle: requirements gathering, architecture, implementation, testing, deployment, and documentation.

## Workflow

```
User Request
  → business-analyst (requirements gathering, TZ creation)
  → architecture-planner (preliminary architecture, cost estimation)
  → project-manager (backlog, tasks)
  → architecture-planner (detailed architecture, ADRs)
  → [optional audits (parallel): security | ui-ux | data]
  → architecture-planner (aggregates audit results)
  → code-implementer (implementation)
  → code-reviewer (review)
  → [parallel]
      comprehensive-test-engineer + performance-analyst
  → devops-infrastructure-engineer (CI/CD, deployment)
  → tech-docs-writer (documentation)
  → project-manager (completion)
```

## Execution Steps

### 1. Initialize

- Read `workflow.yaml` from the extension root — this is the **single source of truth** for all transitions, conditions, and agent definitions
- Initialize iteration counters (all start at 0):
  - `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration`, `infrastructure_review_iteration`
  - `security_verification_iteration`, `ui_verification_iteration`, `data_verification_iteration`
  - `test_iteration`, `performance_iteration`, `documentation_iteration`
- Track workflow state: which agents have run, current phase, collected artifacts

### 2. Start with Business Analyst

**IMMEDIATELY** launch the first agent:
```
agent(subagent_type="business-analyst", prompt="<user's task from above>")
```

The business-analyst will:
- Conduct structured interviews with the user
- Create project context files in `docs/context/`
- Create technical specification (TZ) in `docs/requirements/TZ-*.md`

### 3. Launch Architecture Planner (Preliminary)

After business-analyst completes, launch architecture-planner for preliminary architecture.

**Why this step is not in workflow.yaml:** This is an ad-hoc preparatory step specific to the Full workflow. It creates initial architecture documents that project-manager needs for backlog creation. The formal architecture-planner run (Step 5) is modeled in workflow.yaml and handles detailed architecture with ADRs.

```
agent(subagent_type="architecture-planner", prompt="Create preliminary architecture based on TZ at docs/requirements/TZ-*.md and context at docs/context/")
```

### 4. Launch Project Manager

After preliminary architecture, launch project-manager:
```
agent(subagent_type="project-manager", prompt="Create backlog and sprint plan based on TZ at docs/requirements/TZ-*.md and architecture at docs/architecture/")
```

### 5. Continue with Full Workflow

Follow the standard workflow from `/wf-orc:run`:
- architecture-planner (detailed architecture)
- Optional audits (security, UI-UX, data)
- **code-implementer (per task — see §3a in run.md)**
- code-reviewer
- Parallel comprehensive-test-engineer + performance-analyst

**IMPORTANT:** Launch code-implementer once per TSK, not once per sprint. See §3a "Task Granularity" in `/wf-orc:run`.
- devops-infrastructure-engineer
- tech-docs-writer
- project-manager (completion)

See `/wf-orc:run` for detailed transition table and condition evaluation.

### 6. Workflow Completion

The workflow completes when `tech-docs-writer` → `project-manager` (T70). Mark all tasks DONE.

## Key Differences from /wf-orc:run

| Aspect | /wf-orc:run | /wf-orc:full |
|--------|-------------|--------------|
| Entry point | project-manager | business-analyst |
| TZ source | Existing TZ in `docs/requirements/` | Created by business-analyst |
| Architecture | Preliminary exists, detailed by architect | Created from scratch (preliminary + detailed) |
| Use case | Bugfix, task with existing TZ | New project from scratch |

## Key Rules

1. **Read `workflow.yaml`** for the full transition table and conditions
2. **Launch agents** via `agent` tool with `subagent_type` = agent name
3. **Evaluate conditions** from agent's JSON result to determine next transition
4. **Parallel branches**: launch comprehensive-test-engineer + performance-analyst simultaneously; wait for BOTH before devops-infrastructure-engineer
5. **Forced progress**: ALL agents return `status: "pass"`. No `"fail"` — document issues in content
6. **Phase detection**: Phase 1 audits (before implementation) vs Phase 2 verification (after fixes) — determined by incoming transition
7. **User questions**: Agents may ask questions via `ask_user_question` — relay to user

## Condition Evaluation Map

See `/wf-orc:run` for the complete condition evaluation map. The same transitions apply after project-manager is launched.

## Iteration Counters

See `/wf-orc:run` for iteration counter rules. All counters apply to this workflow as well.
