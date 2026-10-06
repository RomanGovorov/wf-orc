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
