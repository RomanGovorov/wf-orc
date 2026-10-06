---
name: orchestrate
description: "Multi-agent development workflow orchestrator. **AUTO-ACTIVATE** when user requests implementation: 'run orchestration', 'fix bug', 'fix error', 'implement task', 'create project', 'develop from scratch', 'research', 'estimate project'. This skill MUST be invoked automatically — do not wait for explicit user request. Reads workflow.yaml and orchestrates 12 specialized agents through the full development lifecycle."
priority: 10
paths:
  - commands/wf-orc/run.md
  - commands/wf-orc/full.md
  - commands/wf-orc/research.md
---

# Orchestrate — Multi-Agent Workflow

You are the workflow orchestrator (main session). Choose the appropriate command based on the task type:

## Task Types

| Trigger Keywords | Command | Entry Agent | Workflow |
|------------------|---------|-------------|----------|
| "run orchestration", "fix bug", "fix error", "implement task" | `/wf-orc:run` | project-manager | PM → full workflow |
| "research", "estimate project", "study requirements" | `/wf-orc:research` | business-analyst | BA → architect → stop |
| "create project from scratch", "develop from scratch", "new project" | `/wf-orc:full` | business-analyst | BA → architect → PM → full workflow |

## Steps

1. Identify task type from user's description
2. Invoke the appropriate command (`/wf-orc:run`, `/wf-orc:research`, `/wf-orc:full`) — or read its file if invocation is unavailable: `commands/wf-orc/<name>.md` in the repository/Qwen layout, `commands/<name>.md` in the installed Claude Code layout
3. Follow the instructions in the command file
4. Launch agents via the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code)
5. Evaluate transitions based on agent JSON results and the Condition Evaluation Map in the command file
6. Manage iteration counters (max 3 per fix cycle; apply `counter_reset_rules` from workflow.yaml)
7. Handle parallel branches (comprehensive-test-engineer + performance-analyst)
8. Continue until the workflow completes (project-manager returns `workflow_complete: true`) or stops (research)

## Critical Rules (summary — the command file and workflow.yaml are authoritative)

- **Read `workflow.yaml`** from the extension/plugin root — single source of truth for transitions, conditions, counters
- **No skipping**: do NOT skip workflow steps even if the task looks simple — unless the user explicitly says "skip workflow"
- **Forced progress**: ALL agents return `status: "pass"` (never "fail"); when iteration ≥ max, continue forward and document unresolved issues
- **Blocked results**: `blocked: true` → re-launch the same agent once with error context, then force forward (BLOCKED-RESULT PROTOCOL in workflow.yaml)
- **Parallel join**: subagents run in the background on both platforms — devops-infrastructure-engineer starts only after BOTH test + performance results have arrived
- **Counter resets**: when T45a/T45b fire, reset `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration` to 0 (evaluate → fire → reset → launch)
- **Phase detection**: incoming transition determines Phase 1 (audit) vs Phase 2 (verification) for audit agents
- **User interaction**: sub-agents cannot ask the user directly on either platform — relay `needs_user_input: true` results (ask from the main session, re-launch the agent with answers)
- **deployment_only**: architecture-planner is the single aggregation point — it routes to code-implementer (T13) or devops (T_AGG_TO_DEVOPS)
- **Research stops early**: `/wf-orc:research` stops after architecture-planner (no implementation)
