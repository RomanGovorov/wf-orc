<!-- AUTO-GENERATED from templates — DO NOT EDIT manually. Regenerate with: python3 scripts/generate_all.py -->

---
description: Full project workflow — from requirements to deployment
---

# wf-orc — Full Project Workflow

**START NOW:** Launch the `business-analyst` agent using the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code) with the task below. Then follow the workflow instructions to completion.

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
  → [optional audits: security | ui-ux | data]
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

### 0. CRITICAL — No Workflow Skipping

**MUST NOT skip workflow steps**, even if the task seems simple or focused.

- Do NOT skip any required preceding agents in the workflow
- Do NOT skip audits, code-reviewer, tests, or documentation
- Do NOT "optimize" by launching only the agents you think are needed
- The workflow exists for a reason — each agent catches issues others miss

**Exception:** If the user explicitly says "skip workflow" or "just implement X directly", then you may bypass the workflow.


### 1. Initialize

- Read `workflow.yaml` from the extension root — this is the **single source of truth** for all transitions, conditions, and agent definitions
- Initialize iteration counters (all start at 0):
  - `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration`, `infrastructure_review_iteration`
  - `security_verification_iteration`, `ui_verification_iteration`, `data_verification_iteration`
  - `test_iteration`, `performance_iteration`, `documentation_iteration`
- **Counter resets** (`counter_reset_rules` in workflow.yaml): when T45a/T45b fire (workflow advances into the test+perf phase), reset `code_review_iteration`, `test_fix_review_iteration`, `perf_fix_review_iteration` to 0. Strict order: evaluate conditions FIRST → fire → reset → launch. NEVER reset `test_iteration`, `performance_iteration`, `infrastructure_review_iteration`.

- Track workflow state: which agents have run, current phase, collected artifacts

### 2. Start with Business Analyst

**IMMEDIATELY** launch the first agent:
```
Launch the first agent using the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code) with `subagent_type="business-analyst"` and the user's task as prompt.
```

## Orchestrator Verification Protocol

**CRITICAL:** After launching ANY agent, the orchestrator MUST verify the agent's status and result before making decisions. Never assume the agent tool is unavailable without explicit evidence.

### Step-by-Step Verification

#### 1. Launch Agent

**Qwen Code:**
```javascript
const result = await agent(subagent_type="project-manager", prompt="...", run_in_background=false);
```

**Claude Code:**
```javascript
const result = await Agent(subagent_type="project-manager", prompt="...");
// Background agents report via completion notifications
```

#### 2. Verify Agent Status (MANDATORY)

**After EVERY agent launch**, check the agent's status:

**Qwen Code:**
```javascript
// Check agent roster
const agents = await list_agents();
const myAgent = agents.find(a => a.task_id === result.task_id);

if (!myAgent) {
  // Agent not found in roster — this is an error
  throw new Error(`Agent ${result.task_id} not found in roster`);
}

// Verify completion
if (myAgent.status === "completed") {
  // Agent completed successfully — parse result
  const agentResult = parse_json(result.content);
  // Continue workflow based on agentResult
} else if (myAgent.status === "running") {
  // Agent still running — wait for completion
  await wait_for_completion(result.task_id);
} else if (myAgent.status === "failed") {
  // Agent failed — handle error
  throw new Error(`Agent failed: ${myAgent.error}`);
}
```

**Claude Code:**
```javascript
// Background agents report via completion notifications
// Wait for notification before proceeding
// The notification contains the agent's result
```

#### 3. Parse Agent Result

**Extract JSON from agent's output:**

```javascript
// Agent returns JSON in content field
const agentResult = parse_json(result.content);

// Verify required fields
if (!agentResult.status) {
  throw new Error("Agent result missing 'status' field");
}

// Check for special flags
if (agentResult.needs_user_input) {
  // Apply P1 relay protocol — ask user questions
  // Do NOT evaluate transitions yet
  return;
}

if (agentResult.blocked) {
  // Apply BLOCKED-RESULT PROTOCOL
  // Retry once with error context, then force forward
  return;
}
```

#### 4. Evaluate Transitions

**Only after verifying agent status and parsing result:**

```javascript
// Find matching transition
const currentAgent = "project-manager";
const transitions = workflow_yaml.transitions.filter(t => t.from === currentAgent);

for (const transition of transitions) {
  if (evaluate_condition(transition.condition, agentResult)) {
    // Launch next agent
    const nextAgent = transition.to;
    await agent(subagent_type=nextAgent, prompt="...");
    break;
  }
}
```

### Common Mistakes to Avoid

❌ **WRONG:** "Project-manager недоступен" (без проверки статуса)  
✅ **RIGHT:** Проверить `list_agents()` → найти agent → проверить `status`

❌ **WRONG:** "Workflow не работает" (после одного неудачного вызова)  
✅ **RIGHT:** Retry 3 раза с exponential backoff → если все failed → задокументировать и продолжить

❌ **WRONG:** Работать напрямую, пропуская workflow  
✅ **RIGHT:** Всегда следовать workflow — даже если задача кажется простой

### Timeout and Retry Logic

**If agent does not return within expected time:**

```javascript
async function launchAgentWithRetry(agentType, prompt, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const result = await agent(subagent_type=agentType, prompt=prompt);
      
      // Verify status
      const agents = await list_agents();
      const myAgent = agents.find(a => a.task_id === result.task_id);
      
      if (myAgent && myAgent.status === "completed") {
        return result; // Success
      }
      
      if (myAgent && myAgent.status === "failed") {
        throw new Error(`Agent failed: ${myAgent.error}`);
      }
      
    } catch (error) {
      console.error(`Attempt ${attempt} failed:`, error);
      
      if (attempt === maxRetries) {
        // Document error and continue workflow
        return {
          status: "pass",
          blocked: true,
          error: `Agent ${agentType} failed after ${maxRetries} attempts: ${error.message}`
        };
      }
      
      // Exponential backoff
      await sleep(1000 * attempt);
    }
  }
}
```

### Diagnostic Commands

**If unsure about agent status, run diagnostics:**

```bash
# Check agent logs
ls ~/.qwen/projects/<project-hash>/subagents/<session-id>/

# Check agent meta
cat ~/.qwen/projects/<project-hash>/subagents/<session-id>/agent-<type>-<call-id>.meta.json

# Check agent result
tail -20 ~/.qwen/projects/<project-hash>/subagents/<session-id>/agent-<type>-<call-id>.jsonl | jq -r 'select(.type == "assistant") | .message.parts[]?.text // empty' | tail -50
```

### Platform-Specific Notes

**Qwen Code:**
- Named subagents run in background by default
- Use `run_in_background: false` for inline results
- Completion notifications arrive in later turns
- Use `list_agents` to check status

**Claude Code:**
- Background agents report via completion notifications
- Multiple Agent calls in one message run concurrently
- Wait for BOTH completion notifications before proceeding (for parallel branches)
- Use `list_agents` to check status

### Summary Checklist

Before interpreting agent result:

- [ ] Agent launched successfully (no tool error)
- [ ] Agent status checked via `list_agents`
- [ ] Agent status is "completed" (not "running" or "failed")
- [ ] Agent result parsed from JSON
- [ ] Required fields present (`status`, `artifacts`, flags)
- [ ] Special flags handled (`needs_user_input`, `blocked`)
- [ ] Transitions evaluated based on agent result
- [ ] Next agent launched based on matching transition

**NEVER assume agent tool is unavailable without explicit evidence (tool error message).**


The business-analyst will:
- Conduct structured interviews with the user
- Create project context files in `docs/context/`
- Create technical specification (TZ) in `docs/requirements/TZ-*.md`

### 3. Launch Architecture Planner (Preliminary)

After business-analyst completes, launch architecture-planner for preliminary architecture.

**Why this step is not in workflow.yaml:** This is an ad-hoc preparatory step specific to the Full workflow. It creates initial architecture documents that project-manager needs for backlog creation. The formal architecture-planner run (Step 5) is modeled in workflow.yaml and handles detailed architecture with ADRs.

```
Launch architecture-planner with `subagent_type="architecture-planner"` and prompt to create preliminary architecture based on TZ at docs/requirements/TZ-*.md and context at docs/context/
```

### 4. Launch Project Manager

After preliminary architecture, launch project-manager:
```
Launch project-manager with `subagent_type="project-manager"` and prompt to create backlog and sprint plan based on TZ at docs/requirements/TZ-*.md and architecture at docs/architecture/
```

### 5. Continue with Full Workflow (workflow.yaml tracked)

From this point, follow the standard workflow from `/wf-orc:run` — all transitions are tracked in `workflow.yaml`:

- architecture-planner (detailed architecture with ADRs — this is the FORMAL run, separate from the preliminary step 3)
- Optional audits (security, UI-UX, data)
- code-implementer — **IMPORTANT: launch once per TSK, not once per sprint** (see §3a "Task Granularity" in `/wf-orc:run`)
- code-reviewer
- Parallel comprehensive-test-engineer + performance-analyst
- devops-infrastructure-engineer
- tech-docs-writer
- project-manager (completion)

> **State tracking note:** Steps 2-4 above (BA → preliminary architect → PM) are ad-hoc and NOT tracked in `workflow.yaml`. Starting from Step 5, all transitions follow `workflow.yaml` conditions and iteration counters apply normally.

See `/wf-orc:run` for detailed transition table and condition evaluation.

### 6. Workflow Completion

The workflow completes when `project-manager` returns `workflow_complete: true` (after T70 and the PM's documentation review — T70_REV loops are possible). Then mark all tasks DONE.

## Key Differences from /wf-orc:run

| Aspect | /wf-orc:run | /wf-orc:full |
|--------|-------------|--------------|
| Entry point | project-manager | business-analyst |
| TZ source | Existing TZ in `docs/requirements/` | Created by business-analyst |
| Architecture | Preliminary exists, detailed by architect | Created from scratch (preliminary + detailed) |
| Use case | Bugfix, task with existing TZ | New project from scratch |

## Key Rules

1. **Read `workflow.yaml`** for the full transition table and conditions
2. **Launch agents** via the agent launch tool (platform-specific: `agent(subagent_type=...)` in Qwen Code, `Agent(...)` in Claude Code) with `subagent_type` = agent name
3. **Evaluate conditions** from agent's JSON result to determine next transition
4. **Parallel branches**: launch comprehensive-test-engineer + performance-analyst simultaneously; wait for BOTH before devops-infrastructure-engineer
5. **Forced progress**: ALL agents return `status: "pass"`. No `"fail"` — document issues in content
6. **Blocked**: `blocked: true` → re-launch the same agent once with error context, then force forward (BLOCKED-RESULT PROTOCOL in workflow.yaml)
7. **Phase detection**: Phase 1 audits (before implementation) vs Phase 2 verification (after fixes) — determined by incoming transition
8. **User questions**: sub-agents CANNOT ask the user directly on either platform. Relay `needs_user_input: true` results: ask the user from the main session (`AskUserQuestion` in Claude Code, `ask_user_question` in Qwen Code), then re-launch the agent with answers

## Condition Evaluation Map

See `/wf-orc:run` for the complete condition evaluation map. The same transitions apply after project-manager is launched.

## Iteration Counters

See `/wf-orc:run` for iteration counter rules. All counters apply to this workflow as well.
