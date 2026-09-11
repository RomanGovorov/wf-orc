#!/usr/bin/env bash
set -euo pipefail

# Install wf-orc as a Claude Code skills-directory plugin
# Copies to ~/.claude/skills/wf-orc/ (auto-discovered as wf-orc@skills-dir)
#
# Transformations:
#   commands/wf-orc/*.md   -> commands/*.md (flattened + {{args}} -> $ARGUMENTS)
#   skills/, agents/       -> as-is
#   workflow.yaml          -> as-is (single source of truth for the orchestrator)
#
# NOTE: GEMINI.md is NOT copied. Claude Code does not load CLAUDE.md from plugin
# roots — plugins contribute context via skills/commands/agents only. Orchestrator
# context is delivered by the self-contained command files and the `orchestrate`
# skill. Templates already show both platform syntaxes (no tool-name transforms).
#
# Usage:
#   bash scripts/install_claude.sh
#
# Environment:
#   CLAUDE_HOME -- override install target (default: ~/.claude)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
PLUGIN_DIR="$CLAUDE_HOME/skills/wf-orc"

# Cross-platform sed -i (macOS BSD sed requires backup extension)
sed_inplace() {
    if [[ "$(uname)" == "Darwin" ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# Transform Qwen/Gemini args placeholder to Claude Code format
transform_args_placeholder() {
    local file="$1"
    sed_inplace 's/{{args}}/$ARGUMENTS/g' "$file"
}

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

if [[ ! -d "$REPO_ROOT/skills" ]]; then
    echo "Error: skills/ directory not found."
    exit 1
fi

if [[ ! -d "$REPO_ROOT/agents" ]]; then
    echo "Error: agents/ directory not found."
    exit 1
fi

# A#12: Atomic staging — copy to temp directory first, then move into place.
# This prevents a partial installation if any copy fails.
STAGING_DIR="${PLUGIN_DIR}.staging.$$"
trap 'rm -rf "$STAGING_DIR"' EXIT

echo "Staging installation in $STAGING_DIR..."
mkdir -p "$STAGING_DIR"

# 2. (removed) GEMINI.md -> CLAUDE.md copy: Claude Code does not load CLAUDE.md
#    from plugin roots; orchestrator context lives in the commands + orchestrate skill.

# 3. Copy workflow.yaml
cp "$REPO_ROOT/workflow.yaml" "$STAGING_DIR/workflow.yaml"
echo "  ✓ workflow.yaml"

# 4. Copy LICENSE (if exists)
if [[ -f "$REPO_ROOT/LICENSE" ]]; then
    cp "$REPO_ROOT/LICENSE" "$STAGING_DIR/LICENSE"
    echo "  ✓ LICENSE"
fi

# 5. Copy README.md (if exists)
if [[ -f "$REPO_ROOT/README.md" ]]; then
    cp "$REPO_ROOT/README.md" "$STAGING_DIR/README.md"
    echo "  ✓ README.md"
fi

# 6. Copy .claude-plugin/ manifest
mkdir -p "$STAGING_DIR/.claude-plugin"
cp "$REPO_ROOT/.claude-plugin/plugin.json" "$STAGING_DIR/.claude-plugin/plugin.json"
echo "  ✓ .claude-plugin/plugin.json"

# 7. Copy skills/ directory as-is
cp -r "$REPO_ROOT/skills" "$STAGING_DIR/skills"
skill_count=$(find "$STAGING_DIR/skills" -name "SKILL.md" | wc -l)
echo "  ✓ $skill_count skills"

# 8. Copy agents/ directory as-is
cp -r "$REPO_ROOT/agents" "$STAGING_DIR/agents"
agent_count=$(find "$STAGING_DIR/agents" -name "*.md" | wc -l)
echo "  ✓ $agent_count agents"

# 9. Copy commands/wf-orc/*.md -> commands/*.md (flattened for Claude Code)
# Claude Code maps commands/<name>.md → /<plugin>:<name>; subdirectories under
# commands/ are organizational only (no extra namespace segment). Flattening is
# a harmless normalization — both layouts yield /wf-orc:run.
mkdir -p "$STAGING_DIR/commands"
cmd_count=0
for cmd_file in "$REPO_ROOT"/commands/wf-orc/*.md; do
    [[ -f "$cmd_file" ]] || continue
    cmd_basename="$(basename "$cmd_file")"
    cp "$cmd_file" "$STAGING_DIR/commands/"
    transform_args_placeholder "$STAGING_DIR/commands/$cmd_basename"
    cmd_count=$((cmd_count + 1))
done
echo "  ✓ $cmd_count commands (commands/wf-orc/ → commands/, flattened + args transformed)"

# Atomic swap: rename old installation to backup, move staging into place,
# then remove backup. If the move fails, the old installation is still available.
# The trap ensures STAGING_DIR is cleaned up if anything fails before this point.
echo ""
echo "All files staged successfully. Installing..."
BACKUP_DIR="${PLUGIN_DIR}.bak.$$"
if [[ -d "$PLUGIN_DIR" ]]; then
    mv "$PLUGIN_DIR" "$BACKUP_DIR"
fi
mv "$STAGING_DIR" "$PLUGIN_DIR"
rm -rf "$BACKUP_DIR"
trap - EXIT  # Clear the trap since staging dir is now the plugin dir

# Post-install verification: ensure no untransformed placeholders remain
if grep -r '{{[a-zA-Z_]*}}' "$PLUGIN_DIR/commands/" 2>/dev/null; then
    echo "Warning: untransformed {{...}} placeholders found in installed commands"
    echo "  The install script only transforms {{args}} → \$ARGUMENTS."
    echo "  Other placeholders may indicate a template/generation issue."
fi

echo ""
echo "wf-orc installed as plugin (wf-orc@skills-dir)."
echo "Restart Claude Code or run /reload-plugins to activate."
echo ""
echo "Usage:"
echo "  /wf-orc:run <task>        -- Standard workflow (bugfix)"
echo "  /wf-orc:research <task>   -- Research & estimate"
echo "  /wf-orc:full <task>       -- Full project from scratch"
echo "  orchestrate skill         -- Auto-activates on trigger phrases"
