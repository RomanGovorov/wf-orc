## code-implementer Transition Mapping

The code-implementer returns result flags indicating what type of work was completed. The orchestrator uses these flags to determine the next transition:

| Agent Flag | Outgoing Transition | Next Agent |
|------------|---------------------|------------|
| No fix flags (initial implementation or review fixes) | T34 | code-reviewer |
| `security_fixes_complete = true` | T_CODE_TO_SEC | security-auditor |
| `ui_fixes_complete = true` | T_CODE_TO_UI | ui-ux-accessibility-specialist |
| `data_fixes_complete = true` | T_CODE_TO_DATA | data-engineering-architect |
| `test_fixes_complete = true` | T_CODE_TO_TEST | code-reviewer |
| `perf_fixes_complete = true` | T_CODE_TO_PERF | code-reviewer |

**Rule:** Check the JSON result for fix flags. If a flag is present, use the corresponding transition. If no flags are present, use T34 (standard pass to code-reviewer).
