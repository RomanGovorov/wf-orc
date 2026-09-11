## Glossary

| Term | Definition | Example |
|------|------------|---------|
| **Pass** | Agent completed successfully | `status: "pass"` |
| **Complete** | Artifact or phase finished | `security_audit_complete: true` |
| **Iteration** | One cycle of fix-review loop | `code_review_iteration: 2` |
| **Transition** | Move from one agent to another | `T34: code-implementer → code-reviewer` |
| **Artifact** | Output document or file | `system_architecture_document` |
| **Phase** | Stage of audit (1=before impl, 2=after fixes) | `phase: initial_audit_collect` |
| **Parallel Start** | Launch multiple agents simultaneously | `T45a + T45b: test + performance` |
| **Parallel Join** | Wait for multiple agents to complete | `T51_6 + T52_6 → devops` |
| **Forced Progress** | Continue when iteration ≥ max | Document issues, move forward |
| **Blocked** | Agent cannot complete (error case) | `blocked: true` flag |
