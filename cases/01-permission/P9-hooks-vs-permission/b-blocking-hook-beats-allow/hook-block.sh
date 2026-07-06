#!/bin/bash
# PreToolUse hook: exit 2 の blocking hook(「hook で締める」exit-code 経路の実測用)。
# stderr はモデルに返る契約(hooks docs)。発火の証跡として stdin を marker に残す。
dir="$(cd "$(dirname "$0")" && pwd)"
cat > "$dir/hook-ran.marker"
echo "P9_HOOK_BLOCKED: this Write was blocked by a PreToolUse hook (exit 2)" >&2
exit 2
