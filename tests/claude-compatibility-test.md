# Claude Code Compatibility Test

> **TEMPLATE** — This is a test checklist template to be filled in during compatibility testing.
> Copy this file, fill in the test results, and save as `claude-compatibility-test-<date>.md`.

## Test Environment
- **Claude Code version:** [specify version]
- **wf-orc version:** 0.6.2
- **Test date:** [YYYY-MM-DD]
- **Tester:** [name]

## Test Cases

### 1. Installation
- [ ] `python3 scripts/generate_all.py` then `bash scripts/install_claude.sh` — success
- [ ] Plugin auto-discovered as `wf-orc@skills-dir` (`claude plugin list`); no CLAUDE.md in plugin root (not loaded by Claude Code — context comes from commands + orchestrate skill)
- [ ] `/reload-plugins` picks up changes without restart
- [ ] `claude plugin disable wf-orc@skills-dir` / `enable` work

### 2. Commands
- [ ] `/wf-orc:run <task>`, `/wf-orc:research <task>`, `/wf-orc:full <task>` all resolve (flattened `commands/*.md`, single plugin prefix — no `wf-orc:wf-orc:*`)
- [ ] `{{args}}` was transformed to `$ARGUMENTS` in installed copies; user task text is substituted (no literal `$ARGUMENTS`/`{{args}}` in the injected prompt)

### 3. Agents
- [ ] All 12 agents visible as `wf-orc:<name>` subagent types
- [ ] `disallowedTools` honored — agent listing shows "All tools except Agent, agent, Task, task"; agents cannot spawn sub-agents
- [ ] `maxTurns` cap honored (output marked partial at limit on recent builds)
- [ ] Unknown frontmatter keys silently ignored (no load errors)

### 4. User Interaction (C1 regression)
- [ ] Subagents do NOT attempt direct `AskUserQuestion` (removed from all subagents by Claude Code)
- [ ] business-analyst returns `needs_user_input: true` + `questions[]`; orchestrator relays via main-session `AskUserQuestion`; re-launch with answers resumes the interview
- [ ] BA results carry `task_type` in EVERY result

### 5. Workflow Execution
- [ ] Parallel branches: both Agent calls issued in one message run concurrently; orchestrator waits for BOTH completion notifications before devops (background-by-default semantics)
- [ ] Full workflow completes on PM `workflow_complete: true` (T70_REV loops respected)
- [ ] **Counter reset:** T45a/T45b firing resets the three application-review counters; later test-fix review gets a fresh budget (no stale `code_review_iteration >= 3` force-pass)
- [ ] **Blocked protocol:** `blocked: true` → one retry with error context → force forward; counters not incremented
- [ ] **deployment_only routing:** data agent → T23c → architecture-planner aggregation → T_AGG_TO_DEVOPS → devops; no dead-end when security/UI audits ran in parallel
- [ ] Forced progress at iteration ≥ max, incl. `forced: true` results from test-engineer/perf-analyst

### 6. Skills
- [ ] All 14 skills visible as `wf-orc:<skill-name>`; Skill tool resolves the namespaced names
- [ ] `orchestrate` skill activates on trigger phrases and its command-file paths resolve in the installed layout (`commands/<name>.md`)
- [ ] Agent skill tables work with the namespace note (agents invoke `wf-orc:<skill>` exact names)

### 7. Artifacts
- [ ] All agents create expected artifacts (incl. `docs/testing/coverage-report.md`)
- [ ] File paths match documentation (docs/...)

## Results Summary

- **Total tests:** [X]
- **Passed:** [Y]
- **Failed:** [Z]
- **Success rate:** [Y/X * 100]%

## Issues Found

| # | Severity | Description | Workaround |
|---|----------|-------------|------------|
| 1 | High/Medium/Low | [description] | [workaround if any] |

## Notes

[Any additional observations, recommendations, or platform-specific notes]

## Sign-off

- [ ] All critical tests passed
- [ ] No blocking issues found
- [ ] Ready for production use

**Tester signature:** _______________  
**Date:** _______________
