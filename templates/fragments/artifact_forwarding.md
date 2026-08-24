## Artifact Forwarding

Some transitions list artifacts that the source agent did not create. This is intentional — agents pass through context from upstream agents. The orchestrator must ensure these artifacts are available when launching the target agent.

Example: T_SEC_PASS forwards `source_code` from code-implementer to code-reviewer. The orchestrator collects artifacts as they are produced and makes them available to downstream agents.
