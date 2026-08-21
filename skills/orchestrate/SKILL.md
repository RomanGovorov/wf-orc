---
name: orchestrate
description: "Launch multi-agent development workflow. Activates on: 'запусти оркестрацию' → /wf-orc:run, 'исследование', 'оцени проект' → /wf-orc:research, 'создай проект с нуля', 'разработай с нуля' → /wf-orc:full, 'поправь баг', 'исправь ошибку' → /wf-orc:run. Reads workflow.yaml and orchestrates 12 specialized agents through the full development lifecycle."
---

# Orchestrate — Multi-Agent Workflow

You are the workflow orchestrator. Choose the appropriate command based on the task type:

## Task Types

| Trigger Keywords | Command | Entry Agent | Workflow |
|------------------|---------|-------------|----------|
| "запусти оркестрацию", "поправь баг", "исправь ошибку", "реализуй задачу" | `/wf-orc:run` | project-manager | PM → full workflow |
| "исследование", "оцени проект", "изучи требования" | `/wf-orc:research` | business-analyst | BA → architect → stop |
| "создай проект с нуля", "разработай с нуля", "новый проект" | `/wf-orc:full` | business-analyst | BA → architect → PM → full workflow |

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
7. Handle parallel branches (test + performance)
8. Continue until workflow completes or stops (research)

## Key Reminders

- **Always read the command file** for specific workflow instructions
- **Forced progress**: when iteration ≥ max, continue forward regardless of issues
- **Parallel join**: devops starts only after BOTH test AND performance complete
- **Phase detection**: incoming transition determines Phase 1 (audit) vs Phase 2 (verification)
- **User interaction**: agents may ask questions — relay to user
- **Research stops early**: `/wf-orc:research` stops after architecture-planner (no implementation)
