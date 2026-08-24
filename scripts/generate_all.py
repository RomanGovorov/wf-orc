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
import yaml
from pathlib import Path


# Paths
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
FRAGMENTS_DIR = TEMPLATES_DIR / "fragments"
WORKFLOW_PATH = PROJECT_ROOT / "workflow.yaml"


def load_workflow():
    """Load workflow.yaml."""
    try:
        with open(WORKFLOW_PATH, "r") as f:
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

    # Validate agents have required fields
    for agent in workflow["agents"]:
        if "id" not in agent:
            raise ValueError(f"Agent missing 'id' field: {agent}")
        if "name" not in agent:
            raise ValueError(f"Agent '{agent.get('id')}' missing 'name' field")

    # Validate transitions have required fields
    for transition in workflow["transitions"]:
        if "id" not in transition:
            raise ValueError(f"Transition missing 'id' field: {transition}")
        if "from" not in transition:
            raise ValueError(f"Transition '{transition.get('id')}' missing 'from' field")
        if "to" not in transition:
            raise ValueError(f"Transition '{transition.get('id')}' missing 'to' field")

    # Validate iteration_counters have required fields
    for counter_id, counter_data in workflow["iteration_counters"].items():
        if "owner" not in counter_data:
            raise ValueError(f"Counter '{counter_id}' missing 'owner' field")
        if "max" not in counter_data:
            raise ValueError(f"Counter '{counter_id}' missing 'max' field")


def resolve_includes(content):
    """Resolve {{INCLUDE:path}} directives by inserting fragment content."""
    def replace_include(match):
        fragment_path = match.group(1)
        full_path = TEMPLATES_DIR / fragment_path
        if full_path.exists():
            return full_path.read_text().rstrip()
        else:
            return f"<!-- INCLUDE NOT FOUND: {fragment_path} -->"

    # Pattern: {{INCLUDE:path/to/file.md}}
    pattern = r"\{\{INCLUDE:([^}]+)\}\}"
    return re.sub(pattern, replace_include, content)


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
    # Note: business-analyst is excluded — it has no outgoing transitions in workflow.yaml
    agent_order = [a["id"] for a in agents if a["id"] != "business-analyst"]

    for agent in agent_order:
        if agent not in transitions_by_from:
            continue

        agent_transitions = transitions_by_from[agent]

        for t in agent_transitions:
            transition_id = t["id"]
            to_agent = t["to"]
            condition = t["condition"]

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
    content = template_path.read_text()

    # First resolve includes (fragments)
    content = resolve_includes(content)

    # Then resolve generated content from workflow.yaml
    content = resolve_generated(content, workflow)

    return content


def generate_file(template_path, output_path, workflow):
    """Generate a single file from template."""
    try:
        content = process_template(template_path, workflow)
        output_path.write_text(content)
        print(f"Generated {output_path.relative_to(PROJECT_ROOT)}")
    except IOError as e:
        print(f"Error writing {output_path}: {e}")
        raise


def main():
    """Main entry point."""
    try:
        workflow = load_workflow()
        validate_workflow(workflow)
    except (FileNotFoundError, yaml.YAMLError):
        return 1
    except ValueError as e:
        print(f"Validation error: {e}")
        return 1

    # Generate command files
    commands = ["run", "full", "research"]
    for cmd in commands:
        template_path = TEMPLATES_DIR / "commands" / f"{cmd}.md.tmpl"
        output_path = PROJECT_ROOT / "commands" / "wf-orc" / f"{cmd}.md"
        if template_path.exists():
            try:
                generate_file(template_path, output_path, workflow)
            except IOError:
                return 1
        else:
            print(f"Warning: Template not found: {template_path.relative_to(PROJECT_ROOT)}")

    # Generate GEMINI.md
    gemini_template = TEMPLATES_DIR / "GEMINI.md.tmpl"
    gemini_output = PROJECT_ROOT / "GEMINI.md"
    if gemini_template.exists():
        try:
            generate_file(gemini_template, gemini_output, workflow)
        except IOError:
            return 1
    else:
        print(f"Warning: Template not found: {gemini_template.relative_to(PROJECT_ROOT)}")

    print("\nAll files generated successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
