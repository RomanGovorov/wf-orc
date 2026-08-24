---
name: pm-task-tracker
description: Sync tasks and projects with external UI PM dashboard via REST API. Use when creating, updating, or closing tasks in the UI tracker, or when managing projects in the external service. Requires UI_PM_URL and UI_PM_API_KEY environment variables.
priority: 5
---

# PM Task Tracker — UI PM Dashboard Sync

Sync internal backlog tasks with an external UI PM service. The internal backlog (`tasks/backlog.md`, `tasks/active/`, `tasks/done/`) is the single source of truth. UI PM is a read-oriented dashboard.

## When to Use This Skill

- Creating a task that transitions to `IN_PROGRESS` (agent starts working)
- Updating task status to `REVIEW` or `DONE`
- Creating a new project in the tracker
- Completing workflow (Phase 7) — bulk-close all tasks
- Checking current project/task state in the UI dashboard

## Availability Check

Before ANY operation, verify the service is available. If variables are missing or empty — skip all UI PM operations silently. Internal backlog is always the source of truth.

```bash
# Check availability (returns 200 if healthy)
curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${UI_PM_URL}/api/health"
```

If the response is not `200` or the command fails — do not attempt further API calls. Continue with internal backlog only.

## Authentication

All write operations require the `X-API-Key` header:

```
X-API-Key: ${UI_PM_API_KEY}
```

> **Security note:** Do not use `set -x` when executing curl commands with API key — it will log the key to shell output. Use `set +x` before curl if debug mode is enabled.

## Operations

### Pattern 1: Create Project

When starting a new project that should appear in the UI dashboard:

```bash
curl -s -X POST "${UI_PM_URL}/api/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${UI_PM_API_KEY}" \
  -d '{"name": "Project Name", "description": "Brief description"}'
```

Response contains `id` (UUID) — save it for task creation.

### Pattern 2: Create Task

When a task transitions from `BACKLOG` to `IN_PROGRESS`:

```bash
ASSIGNEE=$(git config user.name 2>/dev/null | tr -d '\n')
ASSIGNEE=${ASSIGNEE:-project-manager}
# Escape special characters for JSON (quotes, backslashes)
ASSIGNEE_ESCAPED=$(printf '%s' "$ASSIGNEE" | sed 's/\\/\\\\/g; s/"/\\"/g')

# Use heredoc for JSON body to avoid exposing data in process list
curl -s -X POST "${UI_PM_URL}/api/tasks" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${UI_PM_API_KEY}" \
  -d @- <<EOF
{
  "projectId": "<project-uuid>",
  "title": "TSK-001: Task title",
  "description": "Task description",
  "status": "in_work",
  "priority": "medium",
  "assignee": "${ASSIGNEE_ESCAPED}"
}
EOF
```

Response contains `id` (UUID) — save it in the task file:

```markdown
## Meta
- UI PM ID: `<uuid-from-response>`
```

### Pattern 3: Update Task Status

When task status changes to `REVIEW` or `DONE`:

```bash
curl -s -X PUT "${UI_PM_URL}/api/tasks/<ui-pm-uuid>" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${UI_PM_API_KEY}" \
  -d '{"status": "review"}'
```

Valid statuses: `in_work`, `review`, `done`.

### Pattern 4: Delete Task

When a task is `CANCELLED` internally and should be removed from UI:

```bash
curl -s -X DELETE "${UI_PM_URL}/api/tasks/<ui-pm-uuid>" \
  -H "X-API-Key: ${UI_PM_API_KEY}"
```

### Pattern 5: List Projects and Tasks

For checking current state (e.g., before sync to avoid duplicates):

```bash
# List all projects
curl -s "${UI_PM_URL}/api/projects" -H "X-API-Key: ${UI_PM_API_KEY}"

# List tasks filtered by project and status
curl -s "${UI_PM_URL}/api/tasks?projectId=<uuid>&status=in_work" \
  -H "X-API-Key: ${UI_PM_API_KEY}"
```

## Sync Rules

| Internal Event | UI PM Action | UI PM Status |
|---|---|---|
| Task → `IN_PROGRESS` | Create task | `in_work` |
| Task → `REVIEW` | Update status | `review` |
| Task → `DONE` | Update status | `done` |
| Task → `CANCELLED` | Delete task | — |
| Workflow complete (Phase 7) | Bulk update all remaining to `done` | `done` |
| Task in `BACKLOG` | No action | — |
| Task in `BLOCKED` | No action | — |

## Error Handling

- If `UI_PM_URL` or `UI_PM_API_KEY` is empty/unset — skip silently
- If health check fails — skip silently, log nothing
- If any API call returns non-2xx — skip silently, continue with internal backlog
- Never block workflow on UI PM availability

## Best Practices

1. Save UI PM UUID in task file immediately after creation — needed for all future updates
2. Batch updates at Phase 7 (workflow completion) — update all remaining tasks to `done` in a loop
3. Use `--max-time 5` on all curl calls to avoid hanging on unresponsive service
4. Create the project in UI PM once at project start, reuse the project UUID for all tasks
5. Include TSK ID in task title for cross-referencing: `"TSK-001: Implement auth API"`

## Common Pitfalls

| Mistake | Why It's Bad | Fix |
|---|---|---|
| Syncing BACKLOG tasks to UI PM | Creates noise in dashboard with not-yet-started work | Only sync at IN_PROGRESS or later |
| Hardcoding UI_PM_URL in scripts | Breaks when URL changes, leaks config | Always use `$UI_PM_URL` env var |
| Not saving UI PM UUID | Cannot update/delete task later without it | Save UUID in task file meta section |
| Blocking workflow on API failure | UI PM is optional, not critical path | Use `--max-time 5`, skip on any error |
| Creating duplicate tasks | No dedup if task file has no UUID yet | Check for existing UUID before POST |
