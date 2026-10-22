## User Interaction

Agents may need to ask the user questions (e.g., business-analyst conducting interviews, project-manager clarifying requirements, or any agent facing uncertainty about approach).

### Platform Reality (same on BOTH platforms)

Sub-agents CANNOT ask the user questions directly:

- **Claude Code:** `AskUserQuestion` is removed from every subagent — even if listed in the agent's tools.
- **Qwen Code:** Named subagents have no `ask_user_question` tool.

The orchestrator (main session) MUST relay questions on both platforms. The question tools (`AskUserQuestion` in Claude Code, `ask_user_question` in Qwen Code) are available in the MAIN session — use them there.

### When Agents MUST Ask (All 12 Agents)

Every agent has the "Ask User When Uncertain" section. Agents MUST return `needs_user_input: true` when:

1. **Multiple viable approaches** — 2+ equally valid paths, present with pros/cons
2. **Unknown domain specifics** — entity names, business rules, config values not derivable from code
3. **Architectural trade-offs** — significant consequences (performance vs readability, etc.)
4. **Destructive operations** — before deleting files, overwriting configs

Format: 2-3 options with descriptions + user can provide their own solution.

### Relay Protocol (P1 in workflow.yaml)

When an agent returns `needs_user_input: true`:
1. This is NOT a routing event — do NOT evaluate transitions against this result
2. Extract the `questions` array from the result
3. Ask the user each question from the main session (batch if possible), presenting options
4. Re-launch the SAME agent with: `"User answers: q1='...', q2='...'. Continue from round N."`
5. The agent resumes from where it left off
6. Evaluate transitions only after the agent returns a result WITHOUT `needs_user_input`

For business-analyst: `task_type` is REQUIRED in every result (including `needs_user_input` results) — T_BA_EXIT/T_BA_RESEARCH route on it (protocol P2 in workflow.yaml).

**Note:** Business-analyst uses multi-round interviews. Other agents use `needs_user_input` for one-off decisions when facing uncertainty.
