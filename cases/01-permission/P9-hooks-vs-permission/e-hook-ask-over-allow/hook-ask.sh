#!/bin/bash
# PreToolUse hook: permissionDecision=ask(allow 済みの操作を確認制へ格上げできるかの実測用)。
dir="$(cd "$(dirname "$0")" && pwd)"
cat > "$dir/hook-ran.marker"
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"P9_HOOK_ASK"}}'
