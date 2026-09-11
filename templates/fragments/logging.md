## Workflow Logging

After each transition, log the following for debugging and analysis:

### Log Entry Format
```
[TIMESTAMP] TRANSITION: <transition_id>
  From: <current_agent>
  To: <next_agent>
  Condition: <condition_expression>
  Result: <condition_evaluation_result>
  Iterations: <counter_name>=<value> (if changed)
  Artifacts: <list_of_artifacts>
```

### Example
```
[2026-09-10 14:32:15] TRANSITION: T34
  From: code-implementer
  To: code-reviewer
  Condition: no_fix_flags_present
  Result: TRUE
  Iterations: (unchanged)
  Artifacts: source_code, unit_tests, implementation_report
```

### When to Log
- After every transition evaluation
- When iteration counter increments
- When parallel branches complete
- When workflow completes or errors

### Log Storage
Logs should be stored in `docs/workflow-log.md` (append-only).
