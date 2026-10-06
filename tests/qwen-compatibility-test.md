# Qwen Code Compatibility Test

> **TEMPLATE** — This is a test checklist template to be filled in during compatibility testing.
> Copy this file, fill in the test results, and save as `qwen-compatibility-test-<date>.md`.

## Test Environment
- **Qwen Code version:** [specify version]
- **wf-orc version:** 0.6.3
- **Test date:** [YYYY-MM-DD]
- **Tester:** [name]

## Test Cases

### 1. Installation
- [ ] `qwen extensions install https://github.com/RomanGovorov/wf-orc` — success
- [ ] `gemini-extension.json` converted to `qwen-extension.json`; `contextFileName: GEMINI.md` preserved
- [ ] Extension appears in `qwen extensions list`
- [ ] GEMINI.md context is loaded (orchestrator rules visible without invoking a command)
- [ ] All files copied correctly (agents/ 12 files, skills/ 14 dirs, commands/wf-orc/ 3 files, workflow.yaml)

### 2. Commands
- [ ] `/wf-orc:run test task` — launches project-manager; `{{args}}` substituted (no literal `{{args}}` in prompt)
- [ ] `/wf-orc:research test task` — launches business-analyst
- [ ] `/wf-orc:full test task` — launches business-analyst
- [ ] Commands appear in command list (named from `commands/wf-orc/` subdirectory → `/wf-orc:<name>`)

### 3. Agent Launch
- [ ] `agent(subagent_type="project-manager", prompt="test")` — works
- [ ] `agent(subagent_type="business-analyst", prompt="test")` — works
- [ ] All 12 agents appear in `/agents manage` under "Extension Agents"
- [ ] Named subagents run in the background by default; completion notifications arrive in the main session
- [ ] `run_in_background: false` returns the result inline (foreground opt-out)
- [ ] `disallowedTools: [Agent, agent, Task, task]` honored — agents cannot spawn sub-agents
- [ ] `maxTurns` cap is enforced (agent stops at limit)

### 4. Tools
- [ ] `ask_user_question` is NOT available inside named subagents (per Qwen docs)
- [ ] business-analyst returns `needs_user_input: true` + `questions[]` instead of asking directly
- [ ] Orchestrator relay works: main-session `ask_user_question` → re-launch BA with answers → interview continues
- [ ] BA results carry `task_type` in EVERY result (including `needs_user_input` results)
- [ ] `read_file` / `write_file` / `grep_search` / `run_shell_command` work in agents
- [ ] Skills `priority:` and `paths:` frontmatter parsed without errors

### 5. Workflow Execution
- [ ] Full workflow completes without errors (ends on PM `workflow_complete: true`, not on T70)
- [ ] Parallel branches (test + performance) launch together; devops starts only after BOTH results
- [ ] Iteration counters increment correctly
- [ ] **Counter reset:** when T45a/T45b fire, `code_review_iteration` / `test_fix_review_iteration` / `perf_fix_review_iteration` reset to 0; a later test-fix review does NOT force-pass immediately
- [ ] Forced progress works when iteration ≥ max (incl. `forced: true` results from test-engineer/perf-analyst)
- [ ] **Blocked protocol:** `blocked: true` → one retry with error context → force forward; counters not incremented
- [ ] Phase detection (Phase 1 vs Phase 2) works correctly
- [ ] **deployment_only routing:** data agent returns `deployment_only: true` → T23c to architecture-planner → aggregation → T_AGG_TO_DEVOPS → devops (T13 does NOT fire); no dead-end when security/UI audits ran in parallel

### 6. Artifacts
- [ ] All agents create expected artifacts (incl. `docs/testing/coverage-report.md`)
- [ ] Artifacts passed correctly between agents (T_AGG_TO_DEVOPS forwards security/ui findings to devops)
- [ ] File paths match documentation (docs/...)

### 7. Skills
- [ ] `orchestrate` skill activates on trigger phrases
- [ ] All 14 skills are accessible via `/skills`
- [ ] Skills provide correct information (command-file paths resolve per orchestrate SKILL.md)

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
