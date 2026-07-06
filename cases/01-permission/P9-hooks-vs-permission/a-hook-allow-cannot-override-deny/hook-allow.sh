#!/bin/bash
# PreToolUse hook: 無条件で permissionDecision=allow を返す(「hook で緩める」方向の実測用)。
# 発火の証跡として stdin の hook 入力 JSON を marker に残す(ハーネスの observe.evidenceFile が読む)。
dir="$(cd "$(dirname "$0")" && pwd)"
cat > "$dir/hook-ran.marker"
echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"P9_HOOK_ALLOW_FIRED"}}'
