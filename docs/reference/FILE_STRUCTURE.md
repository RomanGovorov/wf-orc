# File Structure Guide for wf-orc Agents

**Version:** 2.0
**Date:** 2026-10-22
**Purpose:** Centralized reference for documentation and artifact file placement across all wf-orc agents

---

## Overview

wf-orc separates files into two categories:

1. **Final documentation** → `docs/` subdirectories (tracked in git)
2. **Working artifacts** → `.wf-orc/artifacts/` subdirectories (gitignored — disposable, per-run)

**Rule:** If a file is a final project deliverable (readable by humans after the workflow), it goes in `docs/`. If it's a working report used only during the workflow (reviews, test reports, findings), it goes in `.wf-orc/artifacts/`.

**Note:** This file is located in the wf-orc plugin repository itself, not in the target project. It serves as a reference for all wf-orc agents.

---

## Directory Structure

### Final Documentation (`docs/` — tracked in git)

```
docs/
├── architecture/              # Architecture documentation (architecture-planner)
│   ├── system-architecture.md
│   ├── implementation-plan.md
│   ├── data-flow.md
│   ├── component-specifications.md
│   └── adrs/                  # Architecture Decision Records
│       └── ADR-<NNN>_<slug>.md
│
├── requirements/              # Requirements (business-analyst)
│   ├── TZ-<NNN>_<slug>.md    # Technical specifications (immutable)
│   └── cost-estimation.md     # Research workflow only
│
├── context/                   # Project context (business-analyst)
│   ├── project-profile.md
│   ├── stakeholders.md
│   ├── infrastructure.md
│   ├── constraints.md
│   ├── existing-systems.md
│   └── non-functional.md
│
├── security/                  # Security documentation (security-auditor)
│   ├── threat-model.md
│   ├── security-requirements.md
│   └── security-checklist.md
│
├── ui-ux/                     # UI/UX documentation (ui-ux-accessibility-specialist)
│   ├── ui-spec.md
│   ├── accessibility-report.md
│   └── user-flow-diagrams.md
│
├── data/                      # Data architecture (data-engineering-architect)
│   ├── data-models.md
│   ├── pipeline-configurations.md
│   ├── optimized-queries.md
│   └── infrastructure-requirements.md
│
├── testing/                   # Test documentation (comprehensive-test-engineer)
│   └── test-plan.md           # Only final test plan stays here
│
├── performance/               # Performance documentation (performance-analyst)
│   ├── optimization-recommendations.md
│   └── benchmarks.md          # Before/after metrics (append-only)
│
├── infrastructure/            # Infrastructure documentation (devops-infrastructure-engineer)
│   ├── deployment-manifest.md
│   ├── ci-cd-pipeline.md
│   └── monitoring-dashboard.md
│
└── guides/                    # User-facing documentation (tech-docs-writer)
    ├── api/                   # API documentation
    │   ├── api-docs.md
    │   └── openapi.yaml
    ├── user/                  # User guides
    │   └── user-guide.md
    ├── runbooks/              # Operational procedures
    │   └── runbook-<NNN>_<slug>.md
    └── release-notes/         # Release notes
        └── CHANGELOG.md
```

### Working Artifacts (`.wf-orc/artifacts/` — gitignored)

```
.wf-orc/artifacts/
├── context/                   # State files for multi-round agent interactions
│   ├── interview-state.md     # BA interview state (mandatory for multi-round interviews)
│   └── doc-review-state.md    # PM doc review state (mandatory for multi-round reviews)
│
├── implementation/            # Implementation reports (code-implementer)
│   ├── implementation-report.md
│   └── implementation-report-<TSK-ID>.md
│
├── reviews/                   # Code review reports (code-reviewer)
│   └── review-<TSK-ID>.md    # One per task, never merge
│
├── testing/                   # Test reports and bug reports (comprehensive-test-engineer)
│   ├── test-report.md
│   ├── coverage-report.md
│   └── bug-reports/
│       └── BUG-<NNN>_<slug>.md
│
├── performance/               # Performance reports (performance-analyst)
│   ├── profiling-report.md
│   ├── profiling-report-<TSK-ID>.md
│   ├── load-test-results.md
│   ├── load-test-results-<TSK-ID>.md
│   └── optimization-log.md    # Append-only log
│
├── security/                  # Security findings (security-auditor)
│   └── findings/
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── ui-ux/                     # UI/UX findings (ui-ux-accessibility-specialist)
│   └── findings/
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── data/                      # Data findings (data-engineering-architect)
│   ├── data-findings-report.md
│   └── findings/
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── infrastructure/            # Infrastructure review reports (devops-infrastructure-engineer)
│   ├── infrastructure-review.md
│   └── infrastructure-review-<TSK-ID>.md
│
└── workflow/                  # Workflow completion reports (project-manager)
    ├── workflow-complete.md
    └── workflow-complete-<TSK-ID>.md
```

### Task Management (`tasks/` — tracked in git)

```
tasks/
├── backlog.md                 # Product backlog (PM maintains)
├── active/                    # Tasks in progress
│   └── TSK-<NNN>_<slug>.md
├── done/                      # Completed tasks (>7 days → archive)
│   └── TSK-<NNN>_<slug>.md
└── archive/                   # Old completed tasks
    └── TSK-<NNN>_<slug>.md
```

### Infrastructure Code (project root — tracked in git)

```
Dockerfile                     # Docker build (devops-infrastructure-engineer)
docker-compose.yml             # Docker Compose (optional)
infrastructure/
├── terraform/                 # Terraform IaC
│   └── variables.tf
└── k8s/                       # Kubernetes manifests
```

---

## Agent-Specific File Placement

### business-analyst
- **Context files** (final): `docs/context/*.md` (6 files)
- **Requirements** (final): `docs/requirements/TZ-<NNN>_<slug>.md` (immutable)
- **Cost estimation** (final): `docs/requirements/cost-estimation.md` (research only)
- **Interview state** (working): `.wf-orc/artifacts/context/interview-state.md`

### architecture-planner
- **Architecture docs** (final): `docs/architecture/*.md` (4 mandatory files)
- **ADRs** (final): `docs/architecture/adrs/ADR-<NNN>_<slug>.md`

### security-auditor
- **Core docs** (final): `docs/security/*.md` (3 files: threat-model, security-requirements, security-checklist)
- **Findings** (working): `.wf-orc/artifacts/security/findings/PHASE<1|2>-<NNN>_<slug>.md`

### ui-ux-accessibility-specialist
- **Core docs** (final): `docs/ui-ux/*.md` (3 files: ui-spec, accessibility-report, user-flow-diagrams)
- **Findings** (working): `.wf-orc/artifacts/ui-ux/findings/PHASE<1|2>-<NNN>_<slug>.md`

### data-engineering-architect
- **Core docs** (final): `docs/data/*.md` (4 files: data-models, pipeline-configurations, optimized-queries, infrastructure-requirements)
- **Findings** (working): `.wf-orc/artifacts/data/findings/PHASE<1|2>-<NNN>_<slug>.md`

### code-implementer
- **Implementation reports** (working): `.wf-orc/artifacts/implementation/implementation-report*.md`

### code-reviewer
- **Review reports** (working): `.wf-orc/artifacts/reviews/review-<TSK-ID>.md`

### comprehensive-test-engineer
- **Test plan** (final): `docs/testing/test-plan.md`
- **Test/bug reports** (working): `.wf-orc/artifacts/testing/test-report.md`, `coverage-report.md`, `bug-reports/BUG-*.md`

### performance-analyst
- **Benchmarks** (final): `docs/performance/benchmarks.md`
- **Optimization recommendations** (final): `docs/performance/optimization-recommendations.md`
- **Profiling/load reports** (working): `.wf-orc/artifacts/performance/profiling-report*.md`, `load-test-results*.md`, `optimization-log.md`

### devops-infrastructure-engineer
- **Infrastructure docs** (final): `docs/infrastructure/*.md` (3 files: deployment-manifest, ci-cd-pipeline, monitoring-dashboard)
- **Infrastructure review** (working): `.wf-orc/artifacts/infrastructure/infrastructure-review*.md`
- **Infrastructure code**: `Dockerfile`, `infrastructure/terraform/`, `infrastructure/k8s/`

### project-manager
- **Workflow reports** (working): `.wf-orc/artifacts/workflow/workflow-complete*.md`
- **Review state** (working): `.wf-orc/artifacts/context/doc-review-state.md`
- **Task files** (git-tracked): `tasks/active/TSK-*.md`, `tasks/done/TSK-*.md`, `tasks/backlog.md`

### tech-docs-writer
- **API docs** (final): `docs/guides/api/api-docs.md`, `docs/guides/api/openapi.yaml`
- **User guides** (final): `docs/guides/user/user-guide.md`
- **Runbooks** (final): `docs/guides/runbooks/runbook-<NNN>_<slug>.md`
- **Release notes** (final): `docs/guides/release-notes/CHANGELOG.md`

---

## Rules

1. **Final documentation** goes in `docs/` — tracked in git, readable by humans
2. **Working artifacts** go in `.wf-orc/artifacts/` — gitignored, disposable per-run
3. **Never place documentation in the project root** — always use the appropriate subdirectory
4. **Fixed-name files are mandatory** — do not rename or omit them
5. **Sequential numbering** — ADRs, BUGs, PHASE findings, TSKs use sequential numbers never reused
6. **Immutable files** — `docs/requirements/TZ-*.md` files are immutable; create new revisions
7. **Append-only files** — `benchmarks.md` and `optimization-log.md` are append-only
8. **Task files** stay in `tasks/` subdirectories (active/done/archive)

---

## References

- Each agent's `File Naming Notes` section contains agent-specific details
- `workflow.yaml` defines the workflow transitions and agent responsibilities
- `.gitignore` includes `.wf-orc/artifacts/` to keep working artifacts out of version control
