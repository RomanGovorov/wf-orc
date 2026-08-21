# wf-orc

Qwen Code extension for multi-agent development workflow orchestration.

Packages a complete orchestrator + 12 specialized agents + workflow definition into a single installable extension. Invoke via `/wf-orc:run` or let the orchestrate skill auto-activate on task descriptions.

## Documentation

- [Qwen Code Extensions](https://qwenlm.github.io/qwen-code-docs/en/developers/extensions/extension/)
- [Qwen Code Commands](https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/)
- [Qwen Code Skills](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/)

## Features

- **12 specialized agents** covering the full development lifecycle
- **Workflow engine** with conditional transitions, parallel branches, and iteration limits
- **Forced progress** — workflow never deadlocks (max 3 iterations per fix cycle)
- **Phase-aware audits** — initial audits (Phase 1) before implementation, verification (Phase 2) after fixes
- **Interactive** — agents can ask the user questions during execution
- **14 skills** — orchestration + domain-specific patterns for agents

## Structure

```
wf-orc/
├── qwen-extension.json        # Extension manifest
├── QWEN.md                    # Orchestrator context (loaded automatically)
├── workflow.yaml              # Single source of truth for transitions
├── commands/
│   └── wf-orc/
│       ├── run.md             # /wf-orc:run — bugfix (PM → workflow)
│       ├── research.md        # /wf-orc:research — research (BA → architect → stop)
│       └── full.md            # /wf-orc:full — full project (BA → architect → PM → workflow)
├── skills/
│   ├── orchestrate/           # Auto-activation skill (main entry point)
│   ├── python-professional/   # Python patterns for agents
│   ├── api-design-principles/ # API design for agents
│   ├── secure-coding-patterns/# Security patterns for agents
│   ├── database-patterns/     # Database patterns for agents
│   ├── testing-patterns/      # Testing patterns for agents
│   ├── performance-optimization/ # Performance patterns for agents
│   ├── ci-cd-patterns/        # CI/CD patterns for agents
│   ├── observability-patterns/# Observability patterns for agents
│   ├── git-workflow-patterns/ # Git patterns for agents
│   ├── javascript-typescript-professional/ # JS/TS for agents
│   ├── java-professional/     # Java patterns for agents
│   ├── kotlin-professional/   # Kotlin patterns for agents
│   └── pm-task-tracker/       # External PM dashboard integration
└── agents/                    # 12 specialized agents
    ├── project-manager.md
    ├── architecture-planner.md
    ├── security-auditor.md
    ├── ui-ux-accessibility-specialist.md
    ├── data-engineering-architect.md
    ├── code-implementer.md
    ├── code-reviewer.md
    ├── comprehensive-test-engineer.md
    ├── performance-analyst.md
    ├── devops-infrastructure-engineer.md
    ├── tech-docs-writer.md
    └── business-analyst.md
```

## Installation

### Local development (symlink)

```bash
qwen extensions link ./wf-orc
```

### From Git

```bash
qwen extensions install https://github.com/<user>/wf-orc
```

## Usage

### Task Types

| Command | Type | Entry Agent | Use Case |
|---------|------|-------------|----------|
| `/wf-orc:run` | Bugfix | `project-manager` | Fix existing issue, TZ already exists |
| `/wf-orc:research` | Research | `business-analyst` | Research requirements, estimate costs |
| `/wf-orc:full` | Full project | `business-analyst` | New project from scratch |

### Typical Flow

1. **Research phase** (optional): Run `/wf-orc:research` to gather requirements and estimate costs
   - Result: TZ (`docs/requirements/TZ-*.md`), preliminary architecture, cost estimation
   - Decision point: proceed with implementation or stop

2. **Implementation phase**: Run `/wf-orc:run` (if TZ exists) or `/wf-orc:full` (from scratch)
   - `/wf-orc:run`: Starts with `project-manager`, reads existing TZ and architecture
   - `/wf-orc:full`: Starts with `business-analyst`, full cycle from requirements to documentation

### Explicit command

```bash
/wf-orc:research    # Research and estimation
/wf-orc:run         # Implement (TZ already exists)
/wf-orc:full        # Full project from scratch
```

### Auto-activation

Describe your task naturally — the `orchestrate` skill activates on keywords:
- "запусти оркестрацию", "исследование", "оцени проект" → `/wf-orc:research`
- "поправь баг", "исправь ошибку", "реализуй задачу" → `/wf-orc:run`
- "создай проект с нуля", "разработай с нуля" → `/wf-orc:full`

## Workflow

```
User Request
  → project-manager
  → architecture-planner
  → [optional audits: security | ui-ux | data]
  → architecture-planner (aggregates)
  → code-implementer
  → code-reviewer
  → [test || performance] (parallel)
  → devops-infrastructure-engineer
  → tech-docs-writer
  → project-manager (done)
```

## Agents

| Agent | Role | Model |
|-------|------|-------|
| `project-manager` | Backlog, tasks, prioritization | qwen3.7-max |
| `architecture-planner` | Architecture, planning, ADRs | qwen3.7-max |
| `security-auditor` | Security audit (Phase 1 & 2) | qwen3.7-max |
| `ui-ux-accessibility-specialist` | UI/UX audit (Phase 1 & 2) | qwen3.7-max |
| `data-engineering-architect` | Data/pipeline audit (Phase 1 & 2) | qwen3.7-max |
| `code-implementer` | Code implementation & bugfixes | qwen3.7-max |
| `code-reviewer` | Code review & infrastructure review | qwen3.7-max |
| `comprehensive-test-engineer` | Testing & QA | qwen3.7-max |
| `performance-analyst` | Profiling & load testing | qwen3.7-max |
| `devops-infrastructure-engineer` | CI/CD, deployment, monitoring | qwen3.7-max |
| `tech-docs-writer` | Documentation, guides, ADRs | qwen3.7-max |
| `business-analyst` | Requirements (pre-workflow, manual) | qwen3.7-max |

## How It Works

1. **Commands** (`commands/wf-orc/*.md`) — loaded by Qwen Code as slash commands (`/wf-orc:run`)
2. **Skills** (`skills/*/SKILL.md`) — loaded automatically, `orchestrate` auto-activates on keywords
3. **Agents** (`agents/*.md`) — loaded automatically, launched via `agent` tool by orchestrator
4. **Context** (`QWEN.md`) — loaded automatically as orchestrator context
5. **Workflow** (`workflow.yaml`) — single source of truth for transitions and conditions

## Iteration Counters

| Counter | Owner | Max |
|---------|-------|-----|
| `code_review_iteration` | code-reviewer | 3 |
| `infrastructure_review_iteration` | code-reviewer | 3 |
| `security_verification_iteration` | security-auditor | 3 |
| `ui_verification_iteration` | ui-ux-accessibility-specialist | 3 |
| `data_verification_iteration` | data-engineering-architect | 3 |
| `test_iteration` | comprehensive-test-engineer | 3 |
| `performance_iteration` | performance-analyst | 3 |
| `documentation_iteration` | tech-docs-writer | 3 |

**Rule:** When counter ≥ max → force forward progress (document unresolved issues, continue workflow).
