#!/usr/bin/env bash
set -euo pipefail

# Install wf-orc as a Claude Code skills-directory plugin
# Copies to ~/.claude/skills/wf-orc/ (auto-discovered as wf-orc@skills-dir)
#
# Transformations:
#   GEMINI.md              -> CLAUDE.md
#   commands/wf-orc/*.md   -> commands/*.md  (flatten)
#   skills/, agents/       -> as-is
#
# Usage:
#   bash scripts/install_claude.sh
#
# Environment:
#   CLAUDE_HOME -- override install target (default: ~/.claude)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
PLUGIN_DIR="$CLAUDE_HOME/skills/wf-orc"

echo "Installing wf-orc as Claude Code plugin..."
echo "  Source: $REPO_ROOT"
echo "  Target: $PLUGIN_DIR"
echo ""

# Verify source
if [[ ! -f "$REPO_ROOT/GEMINI.md" ]]; then
    echo "Error: GEMINI.md not found. Run 'python3 scripts/generate_all.py' first."
    exit 1
fi

if [[ ! -f "$REPO_ROOT/.claude-plugin/plugin.json" ]]; then
    echo "Error: .claude-plugin/plugin.json not found."
    exit 1
fi

# 1. Clean previous installation
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

# 2. Copy GEMINI.md -> CLAUDE.md
cp "$REPO_ROOT/GEMINI.md" "$PLUGIN_DIR/CLAUDE.md"
echo "  ✓ GEMINI.md -> CLAUDE.md"

# 3. Copy workflow.yaml
cp "$REPO_ROOT/workflow.yaml" "$PLUGIN_DIR/workflow.yaml"
echo "  ✓ workflow.yaml"

# 4. Copy LICENSE (if exists)
if [[ -f "$REPO_ROOT/LICENSE" ]]; then
    cp "$REPO_ROOT/LICENSE" "$PLUGIN_DIR/LICENSE"
    echo "  ✓ LICENSE"
fi

# 5. Copy README.md (if exists)
if [[ -f "$REPO_ROOT/README.md" ]]; then
    cp "$REPO_ROOT/README.md" "$PLUGIN_DIR/README.md"
    echo "  ✓ README.md"
fi

# 6. Copy .claude-plugin/ manifest
mkdir -p "$PLUGIN_DIR/.claude-plugin"
cp "$REPO_ROOT/.claude-plugin/plugin.json" "$PLUGIN_DIR/.claude-plugin/plugin.json"
echo "  ✓ .claude-plugin/plugin.json"

# 7. Copy skills/ directory as-is
cp -r "$REPO_ROOT/skills" "$PLUGIN_DIR/skills"
skill_count=$(find "$PLUGIN_DIR/skills" -name "SKILL.md" | wc -l)
echo "  ✓ $skill_count skills"

# 8. Copy agents/ directory as-is
cp -r "$REPO_ROOT/agents" "$PLUGIN_DIR/agents"
agent_count=$(find "$PLUGIN_DIR/agents" -name "*.md" | wc -l)
echo "  ✓ $agent_count agents"

# 9. Flatten commands/wf-orc/*.md -> commands/*.md
mkdir -p "$PLUGIN_DIR/commands"
cmd_count=0
for cmd_file in "$REPO_ROOT"/commands/wf-orc/*.md; do
    [[ -f "$cmd_file" ]] || continue
    cp "$cmd_file" "$PLUGIN_DIR/commands/"
    cmd_count=$((cmd_count + 1))
done
echo "  ✓ $cmd_count commands (flattened from commands/wf-orc/)"

echo ""
echo "wf-orc installed as plugin (wf-orc@skills-dir)."
echo "Restart Claude Code or run /reload-plugins to activate."
echo ""
echo "Usage:"
echo "  /wf-orc:run <task>        -- Standard workflow (bugfix)"
echo "  /wf-orc:research <task>   -- Research & estimate"
echo "  /wf-orc:full <task>       -- Full project from scratch"
echo "  /wf-orc:orchestrate       -- Auto-activate by context"
