#!/bin/bash
# PreToolUse hook: exit 0・出力なし=「判断しない」。沈黙が承認にならないことの実測用。
dir="$(cd "$(dirname "$0")" && pwd)"
cat > "$dir/hook-ran.marker"
exit 0
