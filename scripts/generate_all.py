#!/usr/bin/env python3
"""
Generate all documentation files from templates + workflow.yaml.

This script processes template files (.tmpl) and generates output files
by resolving {{INCLUDE:path}} and {{GENERATED:type}} directives.

Usage:
    python scripts/generate_all.py

Generated files:
    - commands/wf-orc/run.md
    - commands/wf-orc/full.md
    - commands/wf-orc/research.md
    - GEMINI.md
"""

import re
import sys
import json
from pathlib import Path

# Check for PyYAML dependency
try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
FRAGMENTS_DIR = TEMPLATES_DIR / "fragments"
WORKFLOW_PATH = PROJECT_ROOT / "workflow.yaml"


def load_workflow():
    """Load workflow.yaml."""
    try:
        with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {WORKFLOW_PATH} not found")
        raise
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {WORKFLOW_PATH}: {e}")
        raise


def validate_workflow(workflow):
    """Validate workflow.yaml structure. Raises ValueError if invalid."""
    required_keys = ["agents", "transitions", "iteration_counters"]
    for key in required_keys:
        if key not in workflow:
            raise ValueError(f"workflow.yaml missing required section: '{key}'")
        if not workflow[key]:
            raise ValueError(f"workflow.yaml section '{key}' is empty")

    agents = workflow["agents"]
    transitions = workflow["transitions"]
    counters = workflow["iteration_counters"]

    # Collect agent IDs for reference validation
    agent_ids = set()

    # Validate agents have required fields and no duplicates
    for agent in agents:
        if "id" not in agent:
            raise ValueError(f"Agent missing 'id' field: {agent}")
        if "name" not in agent:
            raise ValueError(f"Agent '{agent.get('id')}' missing 'name' field")
        if agent["id"] in agent_ids:
            raise ValueError(f"Duplicate agent id: '{agent['id']}'")
        agent_ids.add(agent["id"])

    # Validate transitions have required fields and reference valid agents
    transition_ids = set()
    for transition in transitions:
        if "id" not in transition:
            raise ValueError(f"Transition missing 'id' field: {transition}")
        if "from" not in transition:
            raise ValueError(f"Transition '{transition.get('id')}' missing 'from' field")
        if "to" not in transition:
            raise ValueError(f"Transition '{transition.get('id')}' missing 'to' field")
        if transition["id"] in transition_ids:
            raise ValueError(f"Duplicate transition id: '{transition['id']}'")
        transition_ids.add(transition["id"])
        if transition["from"] not in agent_ids:
            raise ValueError(f"Transition '{transition['id']}' references unknown agent: '{transition['from']}'")
        if transition["to"] not in agent_ids and transition["to"] != "_terminal":
            raise ValueError(f"Transition '{transition['id']}' references unknown agent: '{transition['to']}'")

    # Validate iteration_counters have required fields
    for counter_id, counter_data in counters.items():
        if "owner" not in counter_data:
            raise ValueError(f"Counter '{counter_id}' missing 'owner' field")
        if "max" not in counter_data:
            raise ValueError(f"Counter '{counter_id}' missing 'max' field")
        if "description" not in counter_data:
            raise ValueError(f"Counter '{counter_id}' missing 'description' field")
        if counter_data["owner"] not in agent_ids:
            raise ValueError(f"Counter '{counter_id}' references unknown owner: '{counter_data['owner']}'")


def validate_versions():
    """Validate that all plugin manifests have the same version.

    `.claude-plugin/plugin.json` is REQUIRED (install_claude.sh refuses to run
    without it); the other manifests are optional and only warned about.
    """
    manifests = {
        "gemini-extension.json": ("json", False),
        ".claude-plugin/plugin.json": ("json", True),
        ".codex-plugin/plugin.json": ("json", False),
        ".cursor-plugin/plugin.json": ("json", False),
        ".hermes-plugin/plugin.yaml": ("yaml", False),
    }

    versions = {}
    for path_str, (fmt, required) in manifests.items():
        path = PROJECT_ROOT / path_str
        if not path.exists():
            if required:
                raise ValueError(f"Required manifest not found: {path_str}")
            print(f"Warning: manifest not found: {path_str}")
            continue
        with open(path, encoding="utf-8") as f:
            if fmt == "yaml":
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        version = data.get("version")
        # A#13: Present but versionless manifest is an error (not silently skipped)
        if version is None:
            raise ValueError(f"Manifest exists but has no version field: {path_str}")
        versions[path_str] = version

    unique = set(versions.values())
    if len(unique) > 1:
        details = "\n".join(f"  {k}: {v}" for k, v in versions.items() if v)
        raise ValueError(f"Version mismatch across manifests:\n{details}")
    elif len(unique) == 1:
        print(f"Version check: all manifests at {unique.pop()}")
    else:
        print("Warning: no versioned manifests found")


def resolve_includes(content, max_depth=5):
    """Resolve {{INCLUDE:path}} directives by inserting fragment content.

    Supports nested includes up to max_depth levels.
    Preserves one trailing newline from fragments for proper markdown spacing.
    """
    def replace_include(match):
        fragment_path = match.group(1)
        full_path = TEMPLATES_DIR / fragment_path
        if full_path.exists():
            # Strip trailing whitespace but preserve one newline for markdown spacing
            text = full_path.read_text(encoding="utf-8").rstrip()
            return text + "\n" if text else ""
        else:
            return f"<!-- INCLUDE NOT FOUND: {fragment_path} -->"

    # Pattern: {{INCLUDE:path/to/file.md}}
    pattern = r"\{\{INCLUDE:([^}]+)\}\}"
    for _ in range(max_depth):
        new_content = re.sub(pattern, replace_include, content)
        if new_content == content:
            break
        content = new_content
    return content


def generate_agents_table(agents):
    """Generate markdown table of agents from workflow.yaml."""
    lines = [
        "## Agents",
        "",
        "| Agent | Role |",
        "|-------|------|",
    ]

    for agent in agents:
        agent_id = agent["id"]
        role = agent.get("description", "N/A")
        lines.append(f"| `{agent_id}` | {role} |")

    return "\n".join(lines)


def generate_counters_table(counters):
    """Generate markdown table of iteration counters from workflow.yaml."""
    lines = [
        "## Iteration Counters",
        "",
        "| Counter | Owner | Max |",
        "|---------|-------|-----|",
    ]

    for counter_id, counter_data in counters.items():
        owner = counter_data["owner"]
        max_val = counter_data["max"]
        lines.append(f"| `{counter_id}` | {owner} | {max_val} |")

    return "\n".join(lines)


def generate_condition_evaluation_map(agents, transitions):
    """Generate Condition Evaluation Map table from workflow.yaml transitions."""
    lines = [
        "## Condition Evaluation Map",
        "",
        "| Current Agent | Transition | Next Agent | Condition = TRUE when |",
        "|---|---|---|---|",
    ]

    # Group transitions by 'from' agent
    transitions_by_from = {}
    for t in transitions:
        from_agent = t["from"]
        if from_agent not in transitions_by_from:
            transitions_by_from[from_agent] = []
        transitions_by_from[from_agent].append(t)

    # Derive agent order from workflow.yaml agents section
    # Note: business-analyst is excluded — it only appears in /wf-orc:full and /wf-orc:research,
    # not in the standard /wf-orc:run workflow that this map documents.
    agent_order = [a["id"] for a in agents if a["id"] != "business-analyst"]

    for agent in agent_order:
        if agent not in transitions_by_from:
            continue

        agent_transitions = transitions_by_from[agent]

        for t in agent_transitions:
            transition_id = t["id"]
            to_agent = t["to"]
            # Use .get() to avoid KeyError if condition is missing
            condition = t.get("condition", "Always")

            # Format agent name with phase if applicable
            phase = t.get("phase", "")
            if phase == "initial_audit_collect" and agent in ["security-auditor", "ui-ux-accessibility-specialist", "data-engineering-architect"]:
                agent_display = f"{agent} (Phase 1)"
            elif phase == "verification" and agent in ["security-auditor", "ui-ux-accessibility-specialist", "data-engineering-architect"]:
                agent_display = f"{agent} (Phase 2)"
            else:
                agent_display = agent

            # Format condition for readability
            condition_display = f"`{condition}`" if condition else "Always"

            lines.append(f"| {agent_display} | {transition_id} | {to_agent} | {condition_display} |")

    return "\n".join(lines)


def generate_counter_ownership_table(counters, transitions):
    """Generate Counter Ownership table from workflow.yaml."""
    lines = [
        "### Counter Ownership",
        "",
        "| Counter | Incremented when | Owner |",
        "|---------|-----------------|-------|",
    ]

    for counter_id, counter_data in counters.items():
        desc = counter_data.get("description", "N/A")
        owner = counter_data.get("owner", "N/A")
        lines.append(f"| `{counter_id}` | {desc} | {owner} |")

    return "\n".join(lines)


def resolve_generated(content, workflow):
    """Resolve {{GENERATED:type}} directives by generating content from workflow.yaml."""
    agents = workflow.get("agents", [])
    counters = workflow.get("iteration_counters", {})
    transitions = workflow.get("transitions", [])

    def replace_generated(match):
        gen_type = match.group(1)

        if gen_type == "agents_table":
            return generate_agents_table(agents)
        elif gen_type == "counters_table":
            return generate_counters_table(counters)
        elif gen_type == "condition_evaluation_map":
            return generate_condition_evaluation_map(agents, transitions)
        elif gen_type == "counter_ownership_table":
            return generate_counter_ownership_table(counters, transitions)
        else:
            return f"<!-- GENERATED TYPE NOT FOUND: {gen_type} -->"

    # Pattern: {{GENERATED:type}}
    pattern = r"\{\{GENERATED:([^}]+)\}\}"
    return re.sub(pattern, replace_generated, content)


def process_template(template_path, workflow):
    """Process a template file and return generated content."""
    content = template_path.read_text(encoding="utf-8")

    # First resolve includes (fragments)
    content = resolve_includes(content)

    # Then resolve generated content from workflow.yaml
    content = resolve_generated(content, workflow)

    return content


def validate_generated_content(content, output_path):
    """Validate generated content for unresolved directives.

    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check for unresolved includes
    include_errors = re.findall(r"<!-- INCLUDE NOT FOUND: ([^>]+) -->", content)
    for path in include_errors:
        errors.append(f"{output_path}: unresolved include: {path}")

    # Check for unresolved generated types
    gen_errors = re.findall(r"<!-- GENERATED TYPE NOT FOUND: ([^>]+) -->", content)
    for gen_type in gen_errors:
        errors.append(f"{output_path}: unresolved generated type: {gen_type}")

    # A#10: Assert no raw {{INCLUDE: or {{GENERATED: directives remain
    # (would indicate resolve_includes max_depth exceeded or new directive type)
    raw_includes = re.findall(r"\{\{INCLUDE:[^}]+\}\}", content)
    if raw_includes:
        errors.append(f"{output_path}: {len(raw_includes)} raw {{{{INCLUDE:...}}}} directives remain unresolved")

    raw_generated = re.findall(r"\{\{GENERATED:[^}]+\}\}", content)
    if raw_generated:
        errors.append(f"{output_path}: {len(raw_generated)} raw {{{{GENERATED:...}}}} directives remain unresolved")

    return errors


AUTO_GENERATED_HEADER = "<!-- AUTO-GENERATED from templates — DO NOT EDIT manually. Regenerate with: python3 scripts/generate_all.py -->\n\n"


def generate_file(template_path, output_path, workflow):
    """Generate a single file from template."""
    try:
        content = process_template(template_path, workflow)

        # Validate generated content before writing
        errors = validate_generated_content(content, output_path.relative_to(PROJECT_ROOT))
        if errors:
            for error in errors:
                print(f"Error: {error}")
            raise ValueError(f"Generated content has unresolved directives: {output_path}")

        # Prepend AUTO-GENERATED header so readers can tell generated from hand-authored
        content = AUTO_GENERATED_HEADER + content

        output_path.write_text(content, encoding="utf-8")
        print(f"Generated {output_path.relative_to(PROJECT_ROOT)}")
    except IOError as e:
        print(f"Error writing {output_path}: {e}")
        raise


def patch_readme(workflow):
    """Patch README.md by replacing content between GENERATED markers.

    README.md contains <!-- BEGIN GENERATED:type --> / <!-- END GENERATED:type -->
    markers around tables that should stay in sync with workflow.yaml.
    This function replaces the content between those markers with freshly
    generated tables, preserving the markers themselves.
    """
    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        print("Warning: README.md not found, skipping patch")
        return

    content = readme_path.read_text(encoding="utf-8")
    agents = workflow.get("agents", [])
    counters = workflow.get("iteration_counters", {})

    generators = {
        "agents_table": lambda: generate_agents_table(agents),
        "counters_table": lambda: generate_counters_table(counters),
    }

    for gen_type, generator_fn in generators.items():
        pattern = (
            r"(<!-- BEGIN GENERATED:" + re.escape(gen_type) + r" -->\n)"
            r".*?"
            r"(\n<!-- END GENERATED:" + re.escape(gen_type) + r" -->)"
        )
        match = re.search(pattern, content, flags=re.DOTALL)
        if not match:
            raise ValueError(f"README.md missing <!-- BEGIN GENERATED:{gen_type} --> markers — cannot patch tables. Add the markers around the relevant section.")
        # Use lambda to avoid regex injection from backreferences in generated content
        new_content = re.sub(pattern, lambda m: m.group(1) + generator_fn() + m.group(2), content, flags=re.DOTALL)
        if new_content == content:
            print(f"README.md:{gen_type} — already up to date")
        else:
            print(f"README.md:{gen_type} — updated")
        content = new_content

    try:
        readme_path.write_text(content, encoding="utf-8")
        print(f"Patched {readme_path.relative_to(PROJECT_ROOT)}")
    except IOError as e:
        print(f"Error writing {readme_path}: {e}")
        raise


def main():
    """Main entry point."""
    try:
        workflow = load_workflow()
        validate_workflow(workflow)
        validate_versions()
    except (FileNotFoundError, yaml.YAMLError):
        return 1
    except ValueError as e:
        print(f"Validation error: {e}")
        return 1

    # Ensure output directories exist
    output_dir = PROJECT_ROOT / "commands" / "wf-orc"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate command files
    commands = ["run", "full", "research"]
    for cmd in commands:
        template_path = TEMPLATES_DIR / "commands" / f"{cmd}.md.tmpl"
        output_path = PROJECT_ROOT / "commands" / "wf-orc" / f"{cmd}.md"
        if template_path.exists():
            try:
                generate_file(template_path, output_path, workflow)
            except (IOError, ValueError):
                return 1
            # Validate {{args}} placeholder is present (user input entry point)
            generated_content = output_path.read_text(encoding="utf-8")
            if "{{args}}" not in generated_content:
                print(f"Error: {output_path.name} missing {{{{args}}}} placeholder — user input entry point lost!")
                return 1
        else:
            # A#11: Missing command template is fatal (would leave stale output)
            print(f"Error: Template not found: {template_path.relative_to(PROJECT_ROOT)}")
            return 1

    # Generate GEMINI.md (template is REQUIRED — AGENTS.md is generated as its copy;
    # skipping silently would leave a stale AGENTS.md behind)
    gemini_template = TEMPLATES_DIR / "GEMINI.md.tmpl"
    gemini_output = PROJECT_ROOT / "GEMINI.md"
    if gemini_template.exists():
        try:
            generate_file(gemini_template, gemini_output, workflow)
        except (IOError, ValueError):
            return 1
    else:
        print(f"Error: Template not found: {gemini_template.relative_to(PROJECT_ROOT)}")
        return 1

    # Generate AGENTS.md as copy of GEMINI.md for Codex/Cursor
    # These platforms don't resolve file pointers, so inline the content
    agents_output = PROJECT_ROOT / "AGENTS.md"
    if gemini_output.exists():
        try:
            gemini_content = gemini_output.read_text(encoding="utf-8")
            agents_output.write_text(gemini_content, encoding="utf-8")
            print(f"Generated {agents_output.relative_to(PROJECT_ROOT)} (copy of GEMINI.md)")
        except IOError as e:
            print(f"Error writing AGENTS.md: {e}")
            return 1

    # Patch README.md (replace GENERATED marker sections)
    patch_readme(workflow)

    print("\nAll files generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
