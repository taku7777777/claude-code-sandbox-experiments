#!/bin/bash
# PreToolUse hook: exit 0 + JSON permissionDecision=deny(「hook で締める」JSON 経路の実測用)。
# exit 2 (b) とは別経路。reason はモデルに返る。発火の証跡として stdin を marker に残す。
dir="$(cd "$(dirname "$0")" && pwd)"
cat > "$dir/hook-ran.marker"
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"P9_HOOK_JSON_DENY"}}'
