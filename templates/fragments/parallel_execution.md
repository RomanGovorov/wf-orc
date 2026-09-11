## Parallel Branch Synchronization

When launching parallel branches (comprehensive-test-engineer + performance-analyst):

### Execution Model
1. Launch BOTH agents **simultaneously** using separate agent tool calls (in Claude Code: both Agent calls in ONE message — they run concurrently)
2. **Wait for BOTH to complete** before proceeding
3. Only after BOTH return results, evaluate transitions to devops-infrastructure-engineer

### Implementation
Launch both agents in parallel using the platform's agent tool:
- Qwen Code: `agent(subagent_type="...", prompt="...")`
- Claude Code: `Agent(subagent_type="...", prompt="...")`

### Platform-Specific Wait Semantics

- **Claude Code:** Subagents run in the **background by default** — results arrive as completion notifications in later turns. Multiple Agent calls in one message run concurrently. Do NOT proceed past the join until BOTH completion notifications have arrived.

- **Qwen Code:** Named subagents are **background by default** — results arrive via completion notifications. To wait inline instead, pass `run_in_background: false`; or await the background task results (`list_agents` / task notifications) before proceeding. Do NOT assume automatic synchronization — verify both agents returned results.

### Join Condition
`devops-infrastructure-engineer` starts ONLY when:
- comprehensive-test-engineer returned result (PASS or iteration ≥ max)
- **AND** performance-analyst returned result (PASS or iteration ≥ max)

**Critical:** Do NOT launch devops-infrastructure-engineer if only one branch completed. Both must finish before proceeding.
