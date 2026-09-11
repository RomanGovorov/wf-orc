#!/usr/bin/env bash
set -euo pipefail

# Uninstall wf-orc Claude Code plugin
#
# Usage:
#   bash scripts/uninstall_claude.sh
#
# Environment:
#   CLAUDE_HOME -- override install target (default: ~/.claude)

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
PLUGIN_DIR="$CLAUDE_HOME/skills/wf-orc"

echo "Uninstalling wf-orc plugin..."
if [[ -d "$PLUGIN_DIR" ]]; then
    rm -rf "$PLUGIN_DIR"
    echo "  ✓ Removed $PLUGIN_DIR"
else
    echo "  (not installed)"
fi

# Clean up orphan staging/backup dirs from interrupted installs
for stale in "${PLUGIN_DIR}.staging."* "${PLUGIN_DIR}.bak."*; do
    [[ -e "$stale" ]] && rm -rf "$stale" && echo "  ✓ Removed stale $stale"
done

echo "Restart Claude Code to complete uninstall."
