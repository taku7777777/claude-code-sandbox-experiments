#!/bin/bash
# PreToolUse hook (matcher: Bash) for srt-g.
# Fires when the Bash tool runs. Writes TWO markers so we can separate
# "hook fired but $HOME write was blocked" from "hook never fired":
#   1) cwd/workspace firing marker — proves the hook FIRED (cwd is inside srt allowWrite,
#      so this write always succeeds if the hook ran at all).
#   2) $HOME proof — the boundary test. Without srt (builtin~) the hook runs on the host and
#      this succeeds (S1-i). Under srt the whole claude process (and the hook it spawns) is
#      wrapped in Seatbelt, so $HOME (outside allowWrite) EPERMs and the proof never appears.
# Non-blocking (exit 0, no JSON) so the triggering Bash tool still runs normally.
printf 'SRT_G_HOOK_RAN %s\n' "$(date -u +%FT%TZ)" > "$CLAUDE_PROJECT_DIR/srt-g-hook-ran.marker"
printf 'SRT_G_HOOK_WROTE_HOME %s\n' "$(date -u +%FT%TZ)" > "$HOME/srt-g-hook-proof.txt"
exit 0
