# File Structure Guide for wf-orc Agents

**Version:** 1.0  
**Date:** 2026-10-09  
**Purpose:** Centralized reference for documentation file placement across all wf-orc agents

---

## Overview

This document defines the standard directory structure for all documentation artifacts created by wf-orc agents. **All documentation files must be placed in the appropriate subdirectory under `docs/` in the target project** — never in the project root.

**Note:** This file is located in the wf-orc plugin repository itself, not in the target project. It serves as a reference for all wf-orc agents.

---

## Directory Structure

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
├── context/                   # Project context (business-analyst, project-manager)
│   ├── project-profile.md
│   ├── stakeholders.md
│   ├── infrastructure.md
│   ├── constraints.md
│   ├── existing-systems.md
│   ├── non-functional.md
│   └── doc-review-state.md    # PM review state (mandatory fixed name)
│
├── security/                  # Security documentation (security-auditor)
│   ├── threat-model.md
│   ├── security-requirements.md
│   ├── security-checklist.md
│   ├── security-findings-report.md
│   └── findings/              # Phase-specific findings
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── ui-ux/                     # UI/UX documentation (ui-ux-accessibility-specialist)
│   ├── ui-spec.md
│   ├── accessibility-report.md
│   ├── user-flow-diagrams.md
│   └── findings/              # Phase-specific findings
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── data/                      # Data architecture (data-engineering-architect)
│   ├── data-models.md
│   ├── pipeline-configurations.md
│   ├── optimized-queries.md
│   ├── infrastructure-requirements.md
│   ├── data-findings-report.md
│   └── findings/              # Phase-specific findings
│       ├── PHASE1-<NNN>_<slug>.md
│       └── PHASE2-<NNN>_<slug>.md
│
├── implementation/            # Implementation reports (code-implementer)
│   ├── implementation-report.md
│   ├── implementation-report-<TSK-ID>.md
│   └── TSK-<NNN>_implementation-report.md
│
├── testing/                   # Testing documentation (comprehensive-test-engineer)
│   ├── test-plan.md
│   ├── test-report.md
│   ├── coverage-report.md
│   └── bug-reports/           # Bug reports
│       └── BUG-<NNN>_<slug>.md
│
├── performance/               # Performance documentation (performance-analyst)
│   ├── profiling-report.md
│   ├── profiling-report-<TSK-ID>.md
│   ├── load-test-results.md
│   ├── load-test-results-<TSK-ID>.md
│   ├── optimization-recommendations.md
│   ├── benchmarks.md          # Before/after metrics (append-only)
│   └── optimization-log.md    # Append-only log
│
├── infrastructure/            # Infrastructure documentation (devops-infrastructure-engineer)
│   ├── deployment-manifest.md
│   ├── ci-cd-pipeline.md
│   ├── monitoring-dashboard.md
│   └── infrastructure-review.md
│
├── reviews/                   # Code reviews (code-reviewer)
│   └── review-<TSK-ID>.md
│
├── workflow/                  # Workflow documentation (project-manager)
│   ├── workflow-complete.md
│   └── workflow-complete-<TSK-ID>.md
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

---

## Agent-Specific File Placement

### business-analyst
- **Context files**: `docs/context/*.md` (6 files: project-profile, stakeholders, infrastructure, constraints, existing-systems, non-functional)
- **Requirements**: `docs/requirements/TZ-<NNN>_<slug>.md` (immutable, never modify existing)
- **Cost estimation**: `docs/requirements/cost-estimation.md` (research workflow only)

### architecture-planner
- **Architecture docs**: `docs/architecture/*.md` (4 mandatory fixed-name files)
- **ADRs**: `docs/architecture/adrs/ADR-<NNN>_<slug>.md` (sequential numbers, never reused)

### security-auditor
- **Core docs**: `docs/security/*.md` (3 mandatory fixed-name files + findings report)
- **Findings**: `docs/security/findings/PHASE<1|2>-<NNN>_<slug>.md`

### ui-ux-accessibility-specialist
- **Core docs**: `docs/ui-ux/*.md` (3 mandatory fixed-name files)
- **Findings**: `docs/ui-ux/findings/PHASE<1|2>-<NNN>_<slug>.md`

### data-engineering-architect
- **Core docs**: `docs/data/*.md` (4 mandatory files + findings report)
- **Findings**: `docs/data/findings/PHASE<1|2>-<NNN>_<slug>.md`

### code-implementer
- **Implementation reports**: `docs/implementation/implementation-report*.md`

### comprehensive-test-engineer
- **Test docs**: `docs/testing/*.md` (3 mandatory fixed-name files)
- **Bug reports**: `docs/testing/bug-reports/BUG-<NNN>_<slug>.md`

### performance-analyst
- **Performance docs**: `docs/performance/*.md` (profiling, load tests, optimization)
- **Benchmarks**: `docs/performance/benchmarks.md` (append-only)
- **Optimization log**: `docs/performance/optimization-log.md` (append-only)

### devops-infrastructure-engineer
- **Infrastructure docs**: `docs/infrastructure/*.md` (3 mandatory fixed-name files + review report)
- **Infrastructure code**: `Dockerfile`, `docker-compose.yml`, `infrastructure/terraform/`, `infrastructure/k8s/`

### code-reviewer
- **Review reports**: `docs/reviews/review-<TSK-ID>.md` (one per task, never merge)

### project-manager
- **Workflow docs**: `docs/workflow/workflow-complete*.md`
- **Review state**: `docs/context/doc-review-state.md` (mandatory for multi-round reviews)

### tech-docs-writer
- **API docs**: `docs/guides/api/api-docs.md`, `docs/guides/api/openapi.yaml`
- **User guides**: `docs/guides/user/user-guide.md`
- **Runbooks**: `docs/guides/runbooks/runbook-<NNN>_<slug>.md`
- **Release notes**: `docs/guides/release-notes/CHANGELOG.md`

---

## Rules

1. **Never place documentation in the project root** — always use the appropriate `docs/` subdirectory
2. **Fixed-name files are mandatory** — do not rename or omit them
3. **Sequential numbering** — ADRs, BUGs, PHASE findings use sequential numbers that are never reused
4. **Task-specific files** — use `TSK-<NNN>` or `<TSK-ID>` suffix for task-specific reports
5. **Immutable files** — `docs/requirements/TZ-*.md` files are immutable; create new revisions instead
6. **Append-only files** — `benchmarks.md` and `optimization-log.md` are append-only; never remove entries

---

## Migration Guide

If you have existing documentation in the project root, move it to the appropriate `docs/` subdirectory:

```bash
# Implementation reports
mv IMPLEMENTATION_REPORT*.md docs/implementation/

# Performance reports
mv PROFILING_REPORT*.md docs/performance/
mv LOAD_TEST_RESULTS*.md docs/performance/
mv OPTIMIZATION_RECOMMENDATIONS.md docs/performance/

# Infrastructure reports
mv INFRASTRUCTURE_REVIEW*.md docs/infrastructure/

# Workflow reports
mv WORKFLOW_COMPLETE*.md docs/workflow/

# Task-specific reports
mv TSK-*_IMPLEMENTATION_REPORT.md docs/implementation/
```

---

## References

- Each agent's `File Naming Notes` section contains agent-specific details
- `workflow.yaml` defines the workflow transitions and agent responsibilities
- See individual agent documentation in `agents/*.md` for full details
