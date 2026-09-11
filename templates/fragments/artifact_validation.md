## Artifact Validation (Optional)

After an agent completes, the orchestrator MAY validate that critical artifacts exist.

### Critical Artifacts (validate if possible)
- `system_architecture_document` → `docs/architecture/system-architecture.md`
- `implementation_plan` → `docs/architecture/implementation-plan.md`
- `threat_model` → `docs/security/threat-model.md` (if security audit requested)

### Validation Logic
```python
def validate_artifacts(artifacts: list) -> bool:
    for artifact in artifacts:
        path = get_artifact_path(artifact)
        if path and not path.exists():
            log_warning(f"Artifact {artifact} not found at {path}")
            return False
    return True
```

### Handling Missing Artifacts
If critical artifact is missing:
1. Log warning
2. Attempt to continue workflow (agent may have created artifact in non-standard location)
3. If next agent fails due to missing input, retry current agent with explicit artifact requirements

**Note:** This is optional validation. The workflow trusts agents to create artifacts correctly. Validation helps catch edge cases early.
