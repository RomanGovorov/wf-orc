---
name: orchestrate
description: "Launch multi-agent development workflow. Activates on: 'run orchestration' → /wf-orc:run, 'research', 'estimate project' → /wf-orc:research, 'create project from scratch', 'develop from scratch' → /wf-orc:full, 'fix bug', 'fix error' → /wf-orc:run. Reads workflow.yaml and orchestrates 12 specialized agents through the full development lifecycle."
---

# Orchestrate — Multi-Agent Workflow

You are the workflow orchestrator. Choose the appropriate command based on the task type:

## Task Types

| Trigger Keywords | Command | Entry Agent | Workflow |
|------------------|---------|-------------|----------|
| "run orchestration", "fix bug", "fix error", "implement task" | `/wf-orc:run` | project-manager | PM → full workflow |
| "research", "estimate project", "study requirements" | `/wf-orc:research` | business-analyst | BA → architect → stop |
| "create project from scratch", "develop from scratch", "new project" | `/wf-orc:full` | business-analyst | BA → architect → PM → full workflow |

## Steps

1. Identify task type from user's description
2. Read the appropriate command file:
   - `/wf-orc:research` → `commands/wf-orc/research.md`
   - `/wf-orc:run` → `commands/wf-orc/run.md`
   - `/wf-orc:full` → `commands/wf-orc/full.md`
3. Follow the instructions in the command file
4. Launch agents via `agent` tool
5. Evaluate transitions based on agent JSON results
6. Manage iteration counters (max 3 per fix cycle)
7. Handle parallel branches (comprehensive-test-engineer + performance-analyst)
8. Continue until workflow completes or stops (research)

## Key Reminders

- **Always read the command file** for specific workflow instructions
- **Forced progress**: when iteration ≥ max, continue forward regardless of issues
- **Parallel join**: devops-infrastructure-engineer starts only after BOTH comprehensive-test-engineer AND performance-analyst complete
- **Phase detection**: incoming transition determines Phase 1 (audit) vs Phase 2 (verification)
- **User interaction**: agents may ask questions — relay to user
- **Research stops early**: `/wf-orc:research` stops after architecture-planner (no implementation)
